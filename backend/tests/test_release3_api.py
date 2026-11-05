import csv
import gzip
import io
import json

import pytest
from app.api import final_evaluation as api
from app.api.preparation import encode
from app.core.config import Settings
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_final_asset_is_locked_complete_and_models_are_verified():
    d = api.load_final()
    assert len(d["predictions"]) == 365 and len(d["scores"]) == 6
    assert d["primary_model"] == "autoregression"
    assert d["final_test"]["status"] == "evaluated_locked_protocol"
    assert not d["final_test"]["selection_changed"]
    assert len({r["common_dates"]["n"] for r in d["scores"]}) == 1
    assert all(m["last_label"] < "2025-01-01" for m in d["models"].values())
    assert set(json.loads(api.model_bytes(d))) == {
        "ridge",
        "autoregression",
        "random_forest",
        "gradient_boosting",
    }


def test_final_exports_require_auth_and_keep_clean_numeric_calendars(monkeypatch):
    settings = Settings(_env_file=None, admin_api_key="final-test-api-only")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(app) as client:
        for kind in (
            "predictions",
            "metrics",
            "monthly",
            "sensitivity",
            "models",
            "report",
            "test_report",
        ):
            path = "/api/v1/research/release3?download=" + kind
            assert client.get(path).status_code == 401
            response = client.get(path, headers={"X-API-Key": "final-test-api-only"})
            assert response.status_code == 200
            assert "attachment" in response.headers["content-disposition"]
            assert response.headers["cache-control"] == "no-store"
            if kind in ("predictions", "metrics", "monthly", "sensitivity"):
                rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
                assert (
                    len(rows)
                    == {"predictions": 365, "metrics": 6, "monthly": 72, "sensitivity": 3}[kind]
                )
                if kind == "predictions":
                    assert all(r["Operational Date"].startswith("2025-") for r in rows)
                    assert any(r["Observed Energy (million kWh)"] == "" for r in rows)
                    assert "Random Forest Forecast (million kWh)" in rows[0]
            elif kind == "test_report":
                assert "No post-test model switching" in response.text
        assert (
            client.get(
                "/api/v1/research/release3?download=bad",
                headers={"X-API-Key": "final-test-api-only"},
            ).status_code
            == 422
        )


def test_corrupt_final_models_fail_closed(monkeypatch, tmp_path):
    d = api.load_final()
    path = tmp_path / "models.gz"
    path.write_bytes(gzip.compress(b"{}"))
    monkeypatch.setattr(api, "MODELS_ASSET", path)
    with pytest.raises(HTTPException) as error:
        api.model_bytes(d)
    assert error.value.status_code == 503


@pytest.mark.parametrize("change", ["primary", "fit_label", "calendar"])
def test_wrong_final_protocol_is_refused_even_with_valid_fingerprint(monkeypatch, tmp_path, change):
    d = api.load_final()
    if change == "primary":
        d["primary_model"] = "random_forest"
    elif change == "fit_label":
        d["models"]["autoregression"]["last_label"] = "2025-01-01"
    else:
        d["predictions"][0]["date"] = "2024-01-01"
    import hashlib

    d["experiment_id"] = hashlib.sha256(
        encode({k: v for k, v in d.items() if k != "experiment_id"})
    ).hexdigest()
    path = tmp_path / "changed.gz"
    path.write_bytes(gzip.compress(encode(d)))
    monkeypatch.setattr(api, "ASSET", path)
    with pytest.raises(HTTPException) as error:
        api.load_final()
    assert error.value.status_code == 503
