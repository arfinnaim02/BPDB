import csv
import gzip
import io
import json

import pytest
from app.api import experiments as api
from app.core.config import Settings
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_real_comparison_keeps_six_models_common_dates_and_reserved_test():
    d = api.load_comparison()
    assert len(d["predictions"]) == 366 and len(d["validation"]) == 6
    assert len({r["common_dates"]["n"] for r in d["validation"]}) == 1
    assert d["reserved_test"]["metrics"] is None
    assert d["reserved_test"]["predictions"] is None
    assert d["checks"]["neon_writes"] == 0
    assert d["strict_availability_feature_days"] == 0
    models = json.loads(api.comparison_models(d))
    assert set(models) == {"ridge", "autoregression", "random_forest", "gradient_boosting"}


def test_comparison_and_exports_require_authentication(monkeypatch):
    settings = Settings(_env_file=None, admin_api_key="release2-api-test-only")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(app) as client:
        for suffix in ("", "?download=models", "?download=predictions"):
            assert client.get("/api/v1/research/release2" + suffix).status_code == 401
        headers = {"X-API-Key": "release2-api-test-only"}
        for kind in ("predictions", "selection", "models", "report", "test_report"):
            response = client.get("/api/v1/research/release2?download=" + kind, headers=headers)
            assert response.status_code == 200
            assert "attachment" in response.headers["content-disposition"]
            assert response.headers["cache-control"] == "no-store"
            if kind == "predictions":
                rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
                assert len(rows) == 366
                assert all(r["Operational Date"].startswith("2024-") for r in rows)
                assert any(r["Observed target (million kWh)"] == "" for r in rows)
            elif kind == "selection":
                rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
                assert len(rows) == 5 and len({r["Training scored dates"] for r in rows}) == 1
            elif kind == "test_report":
                assert "reserved and not evaluated" in response.text
        assert (
            client.get("/api/v1/research/release2?download=bad", headers=headers).status_code == 422
        )


def test_corrupt_saved_model_asset_is_refused(monkeypatch, tmp_path):
    d = api.load_comparison()
    path = tmp_path / "bad.gz"
    path.write_bytes(gzip.compress(b"{}"))
    monkeypatch.setattr(api, "MODELS_ASSET", path)
    with pytest.raises(HTTPException) as exc:
        api.comparison_models(d)
    assert exc.value.status_code == 503


def test_test_year_or_changed_result_asset_is_refused(monkeypatch, tmp_path):
    d = api.load_comparison()
    d["predictions"][0]["date"] = "2025-01-01"
    path = tmp_path / "bad.gz"
    path.write_bytes(gzip.compress(json.dumps(d).encode()))
    monkeypatch.setattr(api, "COMPARISON_ASSET", path)
    with pytest.raises(HTTPException) as exc:
        api.load_comparison()
    assert exc.value.status_code == 503
