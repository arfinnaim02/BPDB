import copy
import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from importlib.util import find_spec

import pytest
from app.api import reports as api
from app.api.forecasts import read_history
from app.api.monitoring import read_session, read_summary
from app.core.config import Settings
from app.main import app
from app.services.research_report import build_report, methods_markdown, read_report, tables_csv
from fastapi.testclient import TestClient


def test_report_snapshot_is_stable_except_when_evidence_changes(session):
    inventory = read_summary(session).model_dump(mode="json")
    history = read_history(session, 100, include_evidence=True)
    first = build_report(inventory, history, datetime(2026, 11, 7, tzinfo=timezone.utc))
    second = build_report(inventory, history, datetime(2026, 11, 7, 1, tzinfo=timezone.utc))
    assert first["report_id"] == second["report_id"]
    assert first["generated_at"] != second["generated_at"]
    changed = copy.deepcopy(inventory)
    changed["canonical_dates"] += 1
    assert build_report(changed, history)["report_id"] != first["report_id"]
    assert first["effect"]["common_dates"] == 287
    assert first["effect"]["mae_reduction_percent"] == pytest.approx(13.41, abs=0.005)
    assert not session.new and not session.dirty


@pytest.mark.parametrize(
    "field", ["scored_dates", "completed_targets_with_forecast", "completed_targets_attempted"]
)
def test_report_rejects_untraceable_prospective_summary(session, field):
    inventory = read_summary(session).model_dump(mode="json")
    history = read_history(session, 100, include_evidence=True)
    history["summary"][field] += 1
    with pytest.raises(ValueError, match="evidence"):
        build_report(inventory, history)


def test_report_numerical_tables_and_methods_keep_scope_and_missingness(session):
    report = read_report(session)
    rows = list(csv.DictReader(io.StringIO(tables_csv(report).decode("utf-8-sig"))))
    assert len(rows) == 12
    assert {r["Common Dates"] for r in rows if r["Stage"] == "Final test 2025"} == {"287"}
    text = methods_markdown(report)
    assert report["report_id"] in text and "13.41%" in text
    assert "not available" in text and "not a complete submitted thesis" in text
    assert "not a verified point-in-time backtest" in text


def test_report_pdf_is_eighteen_pages_and_contains_retained_results(session):
    pytest.importorskip("reportlab")
    from app.services.report_pdf import pdf_bytes
    from pypdf import PdfReader

    report = read_report(session)
    data = pdf_bytes(report)
    pdf = PdfReader(io.BytesIO(data))
    assert len(pdf.pages) == 18 and data.startswith(b"%PDF") and len(data) < 3_500_000
    text = "\n".join(p.extract_text() for p in pdf.pages)
    assert "13.41%" in text and "15.5000" in text
    assert "Prospective monitoring" in text and "18 / 18" in text
    assert "\u25a0" not in text


@pytest.mark.parametrize("kind", ["models", "daily", "monthly", "scatter"])
def test_vector_figures_include_snapshot_identity_and_units(session, kind):
    pytest.importorskip("reportlab")
    from app.services.report_pdf import svg_bytes

    report = read_report(session)
    data = svg_bytes(report, kind)
    root = ET.fromstring(data)
    assert root.tag.endswith("svg")
    text = "".join(root.itertext())
    assert report["report_id"] in text and "million kWh" in text
    assert b"<image" not in data and b"<script" not in data


def test_report_api_auth_stale_preview_and_all_export_types(monkeypatch, session):
    report = read_report(session)
    monkeypatch.setattr(
        "app.main.get_settings", lambda: Settings(_env_file=None, admin_api_key="report-test-only")
    )
    monkeypatch.setattr(api, "read_report", lambda *_: report)
    app.dependency_overrides[read_session] = lambda: None
    headers = {"X-API-Key": "report-test-only"}
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/research/report").status_code == 401
            assert (
                client.get("/api/v1/research/report?download=json", headers=headers).status_code
                == 409
            )
            assert (
                client.get(
                    "/api/v1/research/report?download=json&expected_id=" + "0" * 64, headers=headers
                ).status_code
                == 409
            )
            assert (
                client.get("/api/v1/research/report?figure=bad", headers=headers).status_code == 422
            )
            exports = ["json", "tables", "methods"] + (
                ["pdf", "figure"] if find_spec("reportlab") else []
            )
            for kind in exports:
                response = client.get(
                    f"/api/v1/research/report?download={kind}&expected_id={report['report_id']}",
                    headers=headers,
                )
                assert response.status_code == 200
                assert response.headers["x-report-id"] == report["report_id"]
                assert response.headers["cache-control"] == "no-store"
                assert "attachment" in response.headers["content-disposition"]
    finally:
        app.dependency_overrides.clear()


def test_summary_evidence_retains_first_issue_even_outside_display_limit(session):
    from app.services.forecasting import retain_issue
    from test_forecasting import NOW, issue, snapshot

    first, _ = retain_issue(session, issue())
    changed = snapshot()
    changed[-1]["value"] = "201"
    later, _ = retain_issue(session, issue(changed, NOW + timedelta(hours=1)))
    history = read_history(session, 1, NOW + timedelta(days=3), include_evidence=True)
    assert history["items"][0]["id"] == later.id
    assert history["summary_evidence"][0]["id"] == first.id
    assert len(history["attempted_target_dates"]) == 1


def test_export_manifest_binds_every_download_and_preserves_snapshot(session, tmp_path):
    pytest.importorskip("reportlab")
    import hashlib
    import json

    from ingestion.export_research_report import export_files

    report = read_report(session)
    export_files(report, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_bytes())
    assert manifest["report_id"] == report["report_id"]
    assert len(manifest["files"]) == 8
    for name, spec in manifest["files"].items():
        data = (tmp_path / name).read_bytes()
        assert len(data) == spec["bytes"]
        assert hashlib.sha256(data).hexdigest() == spec["sha256"]
    assert not session.dirty and not session.new


def test_detailed_diagnostics_match_frozen_common_sample_and_keep_month_gaps(session):
    from app.services.research_detail import KEYS, quantile

    report = read_report(session)
    assert len(report["details"]["monthly_coverage"]) == 12
    assert report["details"]["monthly_coverage"][0]["common_scored"] == 0
    assert len(report["details"]["largest_ols_errors"]) == 15
    for item in report["details"]["common_diagnostics"]:
        assert item["n"] == 287
        assert (
            item["underprediction_days"] + item["overprediction_days"] + item["exact_days"] == 287
        )
        assert item["beats_lag2_days"] + item["ties_lag2_days"] + item["loses_lag2_days"] == 287
        assert item["median_absolute_error"] <= item["p90_absolute_error"]
        assert item["p90_absolute_error"] <= item["p95_absolute_error"]
        assert item["p95_absolute_error"] <= item["maximum_absolute_error"]
        rows = [
            r
            for r in report["test_predictions"]
            if r["actual"] is not None and all(r[k] is not None for k in KEYS)
        ]
        mae = sum(abs(r[item["model"]] - r["actual"]) for r in rows) / len(rows)
        retained = next(s for s in report["test_scores"] if s["model"] == item["model"])
        assert mae == pytest.approx(retained["common_dates"]["mae"])
    errors = [r["absolute_error"] for r in report["details"]["largest_ols_errors"]]
    assert errors == sorted(errors, reverse=True)
    assert quantile([], 0.5) is None and quantile([0, 10], 0.9) == 9
    assert "Monthly matched-date RMSE" in methods_markdown(report)
