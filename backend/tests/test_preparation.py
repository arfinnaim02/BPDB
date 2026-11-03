import hashlib
import io
import json
import zipfile
from datetime import date, datetime, timedelta, timezone

import pytest
from app.api.monitoring import MasterDay, MasterMeasurement, MasterSource, read_session
from app.api.preparation import build_snapshot, bundle, read_snapshot
from app.core.config import Settings
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_missingness import energy


def day(n, value="100", available=True):
    when = date(2024, 1, 1) + timedelta(days=n-1)
    return MasterDay(
        operational_date=when, report_version_id=f"version-{n}", parser_version="fixture",
        available_at=datetime(2024, 1, 1, tzinfo=timezone.utc) if available else None,
        sources=[MasterSource(id=f"source-{n}", url=f"https://example.org/{n}.pdf",
                              sha256="a" * 64, category="page_1")],
        measurements=[MasterMeasurement(metric="energy_generated", value=value,
            unit="million_kWh", zone="national", period="daily", fuel=None,
            source_id=f"source-{n}", source_page=1, raw_text=f"Energy {value}")],
    )


def build(days, **kwargs):
    return build_snapshot(days, "energy_generated", date(2024, 1, 1), date(2024, 1, 15),
                          date(2024, 1, 10), date(2024, 1, 12), **kwargs)


def test_baseline_dense_calendar_splits_and_lineage_are_lossless():
    original = [day(1, "0"), day(3, None), day(11), day(15)]
    result = build(original)
    assert len(result["rows"]) == 15
    assert result["rows"][0]["original_value"] == "0"
    assert result["rows"][0]["state"] == "observed"
    # Existing energy screen holds zero energy for review, without changing it to missing.
    assert result["rows"][0]["prepared_train_value"] is None
    assert result["rows"][0]["review_hold"]
    assert result["rows"][1]["state"] == "no_canonical_record"
    assert result["rows"][2]["state"] == "explicit_null"
    assert result["rows"][10]["prepared_train_value"] is None
    assert result["rows"][14]["prepared_train_value"] is None
    assert [result["splits"][s]["calendar_days"] for s in ("train","validation","test")] == [10,2,3]
    assert all(r["method"] != "past_week_original_v1" for r in result["rows"])
    assert result["original"][0]["sources"][0]["sha256"] == "a" * 64
    assert original[0].measurements[0].value == "0"


def test_train_only_short_gap_uses_original_calendar_week_donor():
    result = build([day(n) for n in range(1,16) if n not in (8,11,14)],
                   policy="past_week_train_only")
    row = result["rows"][7]
    assert row["prepared_train_value"] == "100" and row["original_value"] is None
    assert row["donor_date"] == "2024-01-01" and row["donor_source_id"] == "source-1"
    assert row["observed_target_candidate"] is False
    assert row["method"] == "past_week_original_v1"
    for i in (10,13):
        assert result["rows"][i]["prepared_train_value"] is None
        assert result["rows"][i]["reason"] == "held_out_target_never_filled"
    assert result["splits"]["train"]["estimated_training_days"] == 1


def test_unknown_or_late_donor_availability_blocks_estimate():
    days = [day(n, available=n != 1) for n in range(1,16) if n != 8]
    assert build(days, policy="past_week_train_only")["rows"][7]["reason"] == (
        "donor_availability_unknown")
    days[0].available_at = datetime(2024, 1, 9, tzinfo=timezone.utc)
    assert build(days, policy="past_week_train_only")["rows"][7]["reason"] == (
        "donor_not_available_at_preparation_cutoff")


def test_boundary_long_gap_and_missing_donor_are_not_filled():
    days = [day(n) for n in range(1,16) if n not in (1,8,9,10)]
    result = build(days, policy="past_week_train_only", max_gap=3)
    assert result["rows"][0]["reason"] == "boundary_gap_not_filled"
    assert all(result["rows"][i]["prepared_train_value"] is None for i in (7,8,9))
    days = [day(n) for n in range(1,16) if n not in (7,8)]
    result = build(days, policy="past_week_train_only", max_gap=1)
    assert result["rows"][7]["reason"] == "gap_above_limit"
    result = build([day(n) for n in range(1,16) if n not in (1,8)],
                   policy="past_week_train_only")
    assert result["rows"][7]["reason"] == "no_usable_original_week_donor"


def test_review_hold_preserves_value_and_prevents_donor_use():
    days = [day(n, "-1" if n == 1 else "100") for n in range(1,16) if n != 8]
    result = build(days, policy="past_week_train_only")
    assert result["rows"][0]["original_value"] == "-1"
    assert result["rows"][0]["review_hold"]
    assert result["rows"][0]["prepared_train_value"] is None
    assert result["rows"][7]["prepared_train_value"] is None


def test_snapshot_identity_covers_policy_value_provenance_and_not_input_order():
    days = [day(1), day(15)]
    first = build(days)["snapshot_id"]
    assert build(list(reversed(days)))["snapshot_id"] == first
    assert build(days, policy="past_week_train_only")["snapshot_id"] != first
    days[0].sources[0].sha256 = "b" * 64
    assert build(days)["snapshot_id"] != first
    days[0].measurements[0].value = "99"
    assert build(days)["snapshot_id"] != first


def test_leap_month_totals_are_observed_only_and_not_split_safe_by_assumption():
    days = []
    for n in range(29):
        d = day(n+1, "2")
        d.operational_date = date(2024,2,1) + timedelta(days=n)
        days.append(d)
    result = build_snapshot(days, "energy_generated", date(2024,2,1), date(2024,2,29),
                            date(2024,2,10), date(2024,2,20))
    assert result["months"][0]["observed_month_total"] == "58"
    assert result["months"][0]["split"] == "crosses_split_boundary"
    days[3].measurements[0].value = None
    result = build_snapshot(days, "energy_generated", date(2024,2,1), date(2024,2,29),
                            date(2024,2,10), date(2024,2,20))
    assert result["months"][0]["observed_month_total"] is None


def test_bundle_checksums_and_original_snapshot_are_verifiable():
    result = build([day(1), day(15)])
    with zipfile.ZipFile(io.BytesIO(bundle(result))) as z:
        manifest = json.loads(z.read("manifest.json"))
        assert manifest["snapshot_id"] == result["snapshot_id"]
        for name, details in manifest["files"].items():
            assert hashlib.sha256(z.read(name)).hexdigest() == details["sha256"]
        assert len(json.loads(z.read("original_snapshot.json"))) == 2
        assert b"original_value" in z.read("daily_audit.csv")


@pytest.mark.parametrize("changes", [dict(policy="mean"),dict(max_gap=0),dict(max_gap=4)])
def test_invalid_policy_rejected(changes):
    with pytest.raises(HTTPException) as e:
        build([], **changes)
    assert e.value.status_code == 422


def test_database_snapshot_reuses_dimension_guards_without_writes(session):
    energy(session, date(2024,1,1), "10")
    energy(session, date(2024,1,15), "20")
    result = read_snapshot(session,"energy_generated",date(2024,1,1),date(2024,1,15),
                           date(2024,1,10),date(2024,1,12))
    assert len(result["rows"]) == 15 and not session.new and not session.dirty
    with pytest.raises(HTTPException):
        read_snapshot(session,"energy_generated",date(2023,1,1),date(2024,1,15),
                      date(2024,1,10),date(2024,1,12))


def test_protected_endpoint_validates_and_rejects_stale_download(monkeypatch):
    settings = Settings(_env_file=None,admin_api_key="prep-test-only")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    app.dependency_overrides[read_session] = lambda: None
    monkeypatch.setattr("app.api.preparation.read_snapshot", lambda *args: build([day(1),day(15)]))
    url = "/api/v1/dataset/preparation"
    q = {"metric":"energy_generated","start_date":"2024-01-01","end_date":"2024-01-15",
         "train_end":"2024-01-10","validation_end":"2024-01-12"}
    headers = {"X-API-Key":"prep-test-only"}
    try:
        with TestClient(app) as c:
            assert c.get(url,params=q).status_code == 401
            assert c.get(url,headers=headers).status_code == 422
            preview = c.get(url,params=q,headers=headers)
            assert preview.headers["cache-control"] == "no-store"
            assert "original" not in preview.json()
            stale = c.get(url,params=q | {"download":True,"expected_id":"old"},headers=headers)
            assert stale.status_code == 409
            ok = c.get(url,params=q | {"download":True,
                       "expected_id":preview.json()["snapshot_id"]},headers=headers)
            assert ok.status_code == 200 and ok.headers["content-type"] == "application/zip"
    finally:
        app.dependency_overrides.clear()


def test_observed_zero_unserved_is_not_missing_or_held():
    d = day(1, "0")
    d.measurements[0].metric = "energy_unserved"
    result = build_snapshot([d], "energy_unserved", date(2024,1,1), date(2024,1,15),
                            date(2024,1,10), date(2024,1,12))
    assert result["rows"][0]["prepared_train_value"] == "0"
    assert result["rows"][0]["observed_target_candidate"]
    assert not result["rows"][0]["review_hold"]


def test_future_holdout_values_cannot_change_prepared_training_values():
    days = [day(n) for n in range(1,16) if n != 8]
    before = build(days, policy="past_week_train_only")
    for d in days:
        if d.operational_date > date(2024,1,10):
            d.measurements[0].value = "999999"
    after = build(days, policy="past_week_train_only")
    assert [r["prepared_train_value"] for r in before["rows"][:10]] == [
        r["prepared_train_value"] for r in after["rows"][:10]]


def test_no_recursive_estimate_can_be_used_as_week_donor():
    days = [day(n) for n in range(1,24) if n not in (8,15)]
    result = build_snapshot(days, "energy_generated", date(2024,1,1), date(2024,1,23),
                            date(2024,1,20), date(2024,1,21), "past_week_train_only")
    assert result["rows"][7]["prepared_train_value"] == "100"
    assert result["rows"][14]["prepared_train_value"] is None
    assert result["rows"][14]["reason"] == "no_usable_original_week_donor"
