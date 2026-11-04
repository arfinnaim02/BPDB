import csv
import gzip
import io
from decimal import Decimal

import pytest
from app.api import frozen_analysis as api
from app.api.preparation import build_snapshot, bundle
from app.core.config import Settings
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from ingestion import analyze_frozen as analysis
from ingestion.freeze_research import END, START, TRAIN_END, VALIDATION_END
from test_preparation import day


def test_decimal_statistics_empty_zero_and_sample_standard_deviation():
    assert analysis.describe([])["mean"] is None
    assert analysis.describe([Decimal(0)])["mean"] == "0.000000"
    assert analysis.describe([Decimal(0)])["sample_sd"] is None
    result = analysis.describe([Decimal(1), Decimal(2), Decimal(3)])
    assert result["mean"] == result["median"] == "2.000000"
    assert result["sample_sd"] == "1.000000"


def test_partial_groups_never_scale_or_fill_totals():
    rows = [
        {"original_value": "10", "eligible": True, "review_hold": False},
        {"original_value": None, "eligible": False, "review_hold": False},
        {"original_value": "20", "eligible": False, "review_hold": True},
    ]
    group = analysis.group_rows(rows, lambda _: "test")[0]
    assert group["mean"] == "10.000000" and group["complete_total"] is None
    assert group["observed_days"] == 2 and group["eligible_days"] == 1
    assert group["missing_days"] == 1 and group["held_days"] == 1
    complete = analysis.group_rows(rows[:1], lambda _: "test")[0]
    assert complete["complete_total"] == "10.000000"


def test_trailing_window_never_bridges_gaps_or_uses_future_days(monkeypatch):
    days = [day(n, str(100 + n)) for n in range(1, 18) if n != 8]
    snapshot = build_snapshot(days, "energy_generated", START, END, TRAIN_END, VALIDATION_END)
    monkeypatch.setattr(analysis, "PINNED_SNAPSHOT", snapshot["snapshot_id"])
    monkeypatch.setattr(analysis, "verify_repairs", lambda _: [])
    report = analysis.analyze(bundle(snapshot))
    assert all(r["trailing_7_mean"] is None for r in report["daily"][:6])
    assert report["daily"][6]["trailing_7_mean"] == "104.000000"
    assert all(r["trailing_7_mean"] is None for r in report["daily"][7:14])
    assert report["daily"][14]["trailing_7_mean"] == "112.000000"
    assert all(m["mom_total_percent"] is None for m in report["monthly"])
    assert all(g["complete_total"] is None for g in report["weekday"])


def test_packaged_snapshot_counts_lineage_and_withheld_totals():
    d = api.load_analysis()
    assert (d["calendar_days"], d["observed_days"], d["missing_days"]) == (366, 295, 71)
    assert d["snapshot_id"] == analysis.PINNED_SNAPSHOT
    assert len(d["monthly"]) == 12 and len(d["weekday"]) == 7 and len(d["quarterly"]) == 4
    assert all(p["complete_total"] is None for p in d["monthly"] if not p["complete"])
    assert all(p["mom_total_percent"] is None for p in d["monthly"] if not p["complete"])
    for date in d["repaired_dates"]:
        row = next(r for r in d["daily"] if r["date"] == date)
        assert row["eligible"] and row["source_sha256"] and row["source_url"]


def test_corrupt_asset_fails_closed_without_internal_path(monkeypatch, tmp_path):
    path = tmp_path / "corrupt.gz"
    path.write_bytes(gzip.compress(b'{"snapshot_id":"wrong","analysis_id":"bad"}'))
    monkeypatch.setattr(api, "ASSET", path)
    with pytest.raises(HTTPException) as exc:
        api.load_analysis()
    assert exc.value.status_code == 503 and str(path) not in exc.value.detail


def test_exports_are_authenticated_numeric_and_reject_unknown_tables(monkeypatch):
    settings = Settings(_env_file=None, admin_api_key="frozen-test-only")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(app) as client:
        assert client.get("/api/v1/analytics/frozen-2024").status_code == 401
        headers = {"X-API-Key": "frozen-test-only"}
        for table, count in (("daily", 366), ("monthly", 12), ("quarterly", 4), ("weekday", 7)):
            response = client.get(
                f"/api/v1/analytics/frozen-2024?download={table}", headers=headers
            )
            assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
            rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
            assert len(rows) == count
            assert "source_url" not in rows[0]
        assert (
            client.get("/api/v1/analytics/frozen-2024?download=wrong", headers=headers).status_code
            == 422
        )
