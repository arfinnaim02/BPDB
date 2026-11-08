import gzip
import hashlib
import json

import pytest
from app.api import treatment
from app.core.config import Settings
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_verified_study_scope_and_all_exports():
    report = treatment.load_study()
    assert report["checks"]["training_days"] == 1461
    assert report["checks"]["eligible_originals"] == 1378
    assert report["provisional_candidate"] == "past_original_3"
    assert len(report["summaries"]) == 25
    for kind in treatment.KINDS:
        response = treatment.treatment_study(kind)
        data = response.body
        assert hashlib.sha256(data).hexdigest() == report["exports"][kind]["sha256"]
        assert data.startswith(b"\xef\xbb\xbf")
        assert response.headers["cache-control"] == "no-store"
    assert treatment.treatment_study("methods").media_type == "text/markdown"


def test_missing_corrupt_and_scope_changed_assets_are_sanitized(tmp_path, monkeypatch):
    original = treatment.load_study()
    monkeypatch.setattr(treatment, "ASSETS", tmp_path)
    path = tmp_path / "treatment_study.json.gz"
    for value in (None, b"broken", gzip.compress(b"{}")):
        if value is not None:
            path.write_bytes(value)
        with pytest.raises(HTTPException) as exc:
            treatment.load_study()
        assert exc.value.status_code == 503
        assert str(tmp_path) not in exc.value.detail
    original["checks"]["database_writes"] = 1
    original["study_id"] = hashlib.sha256(
        treatment.encode({k: v for k, v in original.items() if k != "study_id"})
    ).hexdigest()
    path.write_bytes(gzip.compress(treatment.encode(original)))
    with pytest.raises(HTTPException):
        treatment.load_study()


def test_corrupt_export_and_decompression_limit_refused(tmp_path, monkeypatch):
    report = treatment.load_study()
    monkeypatch.setattr(treatment, "ASSETS", tmp_path)
    monkeypatch.setattr(treatment, "load_study", lambda: report)
    (tmp_path / "treatment_summary.csv.gz").write_bytes(gzip.compress(b"wrong"))
    with pytest.raises(HTTPException) as exc:
        treatment.treatment_study("summary")
    assert exc.value.status_code == 503
    path = tmp_path / "big.gz"
    path.write_bytes(gzip.compress(b"0123456789"))
    with pytest.raises(ValueError, match="too large"):
        treatment.unpack(path, 5)


def test_study_routes_authenticate_and_bound_downloads(monkeypatch):
    settings = Settings(_env_file=None, admin_api_key="study-test-key")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(app) as client:
        path = "/api/v1/research/treatment-study"
        assert client.get(path).status_code == 401
        assert client.get(path + "?download=summary").status_code == 401
        headers = {"X-API-Key": "study-test-key"}
        assert client.get(path + "?download=../secrets", headers=headers).status_code == 422
        result = client.get(path, headers=headers)
        assert result.status_code == 200
        assert json.loads(result.content)["checks"]["database_writes"] == 0
        for kind in (*treatment.KINDS, "methods", "report"):
            response = client.get(path + "?download=" + kind, headers=headers)
            assert response.status_code == 200
            assert "attachment" in response.headers["content-disposition"]
