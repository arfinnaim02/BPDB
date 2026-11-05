import csv
import gzip
import io
import json

import pytest
from app.api import experiments
from app.core.config import Settings
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_real_experiment_identity_coverage_and_reserved_test():
    d = experiments.load_experiment()
    assert d["model"]["rows"] > 60 and len(d["predictions"]) == 366
    assert d["reserved_test"]["metrics"] is None and d["reserved_test"]["predictions"] is None
    assert all(r["date"].startswith("2024-") for r in d["predictions"])
    assert len({r["common_dates"]["n"] for r in d["validation"]}) == 1
    assert d["strict_availability_feature_days"] == 0


def test_experiment_corruption_and_test_evaluation_fail_closed(monkeypatch, tmp_path):
    d = experiments.load_experiment()
    d["reserved_test"]["metrics"] = {"mae": 0}
    path = tmp_path / "corrupt.gz"
    path.write_bytes(gzip.compress(json.dumps(d).encode()))
    monkeypatch.setattr(experiments, "ASSET", path)
    with pytest.raises(HTTPException) as error:
        experiments.load_experiment()
    assert error.value.status_code == 503


def test_authenticated_report_and_numeric_prediction_export(monkeypatch):
    settings = Settings(_env_file=None, admin_api_key="release1-api-test-only")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(app) as client:
        assert client.get("/api/v1/research/release1").status_code == 401
        headers = {"X-API-Key": "release1-api-test-only"}
        response = client.get("/api/v1/research/release1?download=predictions", headers=headers)
        assert response.status_code == 200
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        assert len(rows) == 366 and all(r["Operational Date"].startswith("2024-") for r in rows)
        assert any(not r["Observed target (million kWh)"] for r in rows)
        report = client.get("/api/v1/research/release1?download=test_report", headers=headers)
        assert report.status_code == 200 and "reserved and not evaluated" in report.text
        assert (
            client.get("/api/v1/research/release1?download=bad", headers=headers).status_code == 422
        )
