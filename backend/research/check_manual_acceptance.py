"""Read-only backend acceptance of the published manual checklist. No model fitting."""

import csv
import hashlib
import io
import json
import zipfile
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import app.main as main_module
from app.api.monitoring import read_session
from app.api.preparation import encode
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text

KEY = "temporary-read-only-acceptance-key"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/manual_acceptance"
FEB = {
    "start_date": "2025-02-01",
    "train_end": "2025-02-14",
    "validation_end": "2025-02-21",
    "end_date": "2025-02-28",
    "policy": "observed_only",
}
JAN = {
    "start_date": "2025-01-01",
    "train_end": "2025-01-15",
    "validation_end": "2025-01-22",
    "end_date": "2025-01-31",
    "policy": "observed_only",
}


def inspect_zip(data, days):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert set(z.namelist()) == {
            "manifest.json",
            "original_snapshot.json",
            "daily_audit.csv",
            "daily_values.csv",
            "monthly_observed.csv",
        }
        manifest = json.loads(z.read("manifest.json"))
        for name, info in manifest["files"].items():
            value = z.read(name)
            assert len(value) == info["bytes"]
            assert hashlib.sha256(value).hexdigest() == info["sha256"]
        audit = list(csv.DictReader(io.StringIO(z.read("daily_audit.csv").decode("utf-8-sig"))))
        values = list(csv.DictReader(io.StringIO(z.read("daily_values.csv").decode("utf-8-sig"))))
        months = list(
            csv.DictReader(io.StringIO(z.read("monthly_observed.csv").decode("utf-8-sig")))
        )
        assert len(audit) == len(values) == days
        assert len({r["operational_date"] for r in audit}) == days
        assert [r["operational_date"] for r in audit] == sorted(
            r["operational_date"] for r in audit
        )
        assert all(r["method"] not in {"past_week_original_v1"} for r in audit)
        assert all(r["prepared_train_value"] == "" for r in audit if r["split"] != "train")
        missing = [r for r in audit if r["original_value"] == ""]
        assert all(r["prepared_train_value"] == "" for r in missing)
        original_header = "Original " + manifest["config"]["label"]
        prepared_header = "Prepared Training " + manifest["config"]["label"]
        for a, v in zip(audit, values, strict=True):
            assert v["Operational Date"] == a["operational_date"]
            assert v[original_header] == a["original_value"]
            assert v[prepared_header] == a["prepared_train_value"]
            for header in (original_header, prepared_header):
                if v[header]:
                    assert Decimal(v[header]).is_finite()
        return {
            "snapshot_id": manifest["snapshot_id"],
            "manifest_checksums": "passed",
            "csv_rows": len(audit),
            "missing_original_cells": len(missing),
            "original_zero_cells": sum(
                Decimal(r["original_value"]) == 0 for r in audit if r["original_value"]
            ),
            "held_rows": sum(r["review_hold"] == "True" for r in audit),
            "estimated_rows": sum(r["method"] == "past_week_original_v1" for r in audit),
            "monthly_totals": [r["observed_month_total"] for r in months],
            "blank_preservation": "passed",
            "original_decimal_cells": "passed",
        }


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []
    with contextmanager(read_session)() as db:
        assert db.get_bind().dialect.name == "postgresql"
        assert db.scalar(text("SHOW transaction_read_only")) == "on"
    checks.append({"test": "postgresql_read_only_transaction", "status": "passed"})
    original_settings = main_module.get_settings
    settings = original_settings().model_copy(update={"admin_api_key": SecretStr(KEY)})
    main_module.get_settings = lambda: settings
    headers = {"X-API-Key": KEY}
    cases = {}
    try:
        with TestClient(main_module.app) as client:
            profile_path = "/api/v1/dataset/research-profiles"
            assert client.get(profile_path).status_code == 401
            response = client.get(profile_path, headers=headers)
            assert response.status_code == 200
            profiles = response.json()
            assert len(profiles["variables"]) == 13
            assert all(p["joint_complete_eligible_dates"] is None for p in profiles["profiles"])
            assert response.headers["cache-control"] == "no-store"
            (OUT / "profiles.json").write_bytes(response.content)
            checks.append(
                {"test": "authenticated_profiles_and_no_readiness_invention", "status": "passed"}
            )
            path = "/api/v1/dataset/preparation"
            assert client.get(path, params={**FEB, "metric": "gas_supplied"}).status_code == 401
            for name, metric, window, days in (
                ("gas_feb", "gas_supplied", FEB, 28),
                ("energy_jan", "energy_generated", JAN, 31),
                ("unserved_feb", "energy_unserved", FEB, 28),
            ):
                query = {**window, "metric": metric}
                preview = client.get(path, params=query, headers=headers)
                assert preview.status_code == 200, (name, preview.status_code)
                payload = preview.json()
                assert all(s["estimated_training_days"] == 0 for s in payload["splits"].values())
                if name == "gas_feb":
                    assert [
                        payload["splits"][s]["calendar_days"]
                        for s in (
                            "train",
                            "validation",
                            "test",
                        )
                    ] == [14, 7, 7]
                (OUT / (name + "_preview.json")).write_bytes(preview.content)
                downloaded = client.get(
                    path,
                    params={
                        **query,
                        "download": "true",
                        "expected_id": payload["snapshot_id"],
                    },
                    headers=headers,
                )
                assert downloaded.status_code == 200
                assert "attachment" in downloaded.headers["content-disposition"]
                assert downloaded.headers["cache-control"] == "no-store"
                assert downloaded.headers["content-type"] == "application/zip"
                (OUT / (name + ".zip")).write_bytes(downloaded.content)
                result = inspect_zip(downloaded.content, days)
                assert result["snapshot_id"] == payload["snapshot_id"]
                if name == "energy_jan":
                    assert result["missing_original_cells"] > 0
                    assert all(v == "" for v in result["monthly_totals"])
                if name == "unserved_feb":
                    assert result["original_zero_cells"] > 0
                cases[name] = result
                checks.append({"test": name + "_preview_export_and_csv", "status": "passed"})
            for metric in (
                "day_peak_demand",
                "minimum_generation",
                "energy_demand",
                "energy_unserved",
                "maximum_temperature",
                "gas_supplied",
                "production_cost_per_kwh",
                "total_production_cost",
            ):
                blocked = client.get(
                    path,
                    params={
                        **FEB,
                        "metric": metric,
                        "policy": "past_week_train_only",
                    },
                    headers=headers,
                )
                assert blocked.status_code == 422
                assert "modern-layout-only" in blocked.json()["detail"]
            checks.append({"test": "all_eight_modern_policy_bypasses_blocked", "status": "passed"})
            stale = client.get(
                path,
                params={
                    **FEB,
                    "metric": "gas_supplied",
                    "download": "true",
                    "expected_id": "0" * 64,
                },
                headers=headers,
            )
            assert stale.status_code == 409
            checks.append({"test": "stale_snapshot_download_refused", "status": "passed"})
            for changed in (
                {"start_date": "2025-02-30"},
                {"train_end": "2025-03-01"},
                {"metric": "unknown"},
                {"policy": "fill_all"},
            ):
                invalid = client.get(
                    path,
                    params={
                        **FEB,
                        "metric": "gas_supplied",
                        **changed,
                    },
                    headers=headers,
                )
                assert invalid.status_code == 422
            checks.append({"test": "invalid_dates_metric_policy_refused", "status": "passed"})
    finally:
        main_module.get_settings = original_settings
    report = {
        "status": "passed",
        "checks": checks,
        "real_data_cases": cases,
        "database_writes": 0,
        "production_models_changed": 0,
        "scope": (
            "Current FastAPI application exercised against live Neon in read-only sessions, "
            "using temporary authentication only in this ephemeral test process. "
            "Not a signed-in production-browser test; no forecasting experiment executed."
        ),
    }
    (OUT / "verification.json").write_bytes(encode(report))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        raise SystemExit("Manual-check acceptance failed: " + type(exc).__name__) from None
