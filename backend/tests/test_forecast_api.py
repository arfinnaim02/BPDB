import csv
import io
from types import SimpleNamespace

from app.api import forecasts as api
from app.api.monitoring import read_session
from app.core.config import Settings
from app.main import app
from fastapi.testclient import TestClient
from test_forecasting import NOW, issue


def test_empty_forecast_history_has_no_invented_values_or_accuracy(session):
    result = api.read_history(session, 20, NOW)
    assert result["items"] == [] and result["summary"]["scored_dates"] == 0
    assert result["summary"]["mae"] is None and result["summary"]["rmse"] is None


def test_forecast_api_auth_bounds_and_readonly_exports(monkeypatch, session):
    report = api.read_history(session, 20, NOW)
    monkeypatch.setattr(
        "app.main.get_settings",
        lambda: Settings(_env_file=None, admin_api_key="forecast-test-only"),
    )
    monkeypatch.setattr(api, "read_history", lambda *_: report)
    app.dependency_overrides[read_session] = lambda: SimpleNamespace(get=lambda *_: None)
    headers = {"X-API-Key": "forecast-test-only"}
    try:
        with TestClient(app) as client:
            for path in (
                "/api/v1/forecasts",
                "/api/v1/forecasts?download=csv",
                "/api/v1/forecasts/" + "a" * 64,
            ):
                assert client.get(path).status_code == 401
            assert client.get("/api/v1/forecasts?limit=0", headers=headers).status_code == 422
            assert client.get("/api/v1/forecasts?limit=101", headers=headers).status_code == 422
            assert client.get("/api/v1/forecasts?download=bad", headers=headers).status_code == 422
            assert client.get("/api/v1/forecasts/bad", headers=headers).status_code == 422
            assert client.get("/api/v1/forecasts/" + "a" * 64, headers=headers).status_code == 404
            assert client.get("/api/v1/forecasts", headers=headers).json()["summary"]["mae"] is None
            response = client.get("/api/v1/forecasts?download=csv", headers=headers)
            assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
            assert "attachment" in response.headers["content-disposition"]
            assert len(list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))) == 1
            assert client.post("/api/v1/forecasts", headers=headers).status_code == 405
    finally:
        app.dependency_overrides.clear()


def test_forecast_detail_retains_frozen_sources_and_future_actual_is_blank(monkeypatch):
    row = SimpleNamespace(**issue())
    app.dependency_overrides[read_session] = lambda: SimpleNamespace(get=lambda *_: row)
    monkeypatch.setattr(
        "app.main.get_settings",
        lambda: Settings(_env_file=None, admin_api_key="forecast-test-only"),
    )
    monkeypatch.setattr(api, "outcomes_for", lambda *_: {})
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/forecasts/" + row.id, headers={"X-API-Key": "forecast-test-only"}
            )
            d = response.json()
            assert d["outcome"] is None and len(d["payload"]["used_inputs"]) == 9
            assert all(r["source_sha256"] for r in d["payload"]["used_inputs"])
            assert response.headers["cache-control"] == "no-store"
    finally:
        app.dependency_overrides.clear()


def test_forecast_csv_keeps_missing_actual_and_error_blank():
    row = SimpleNamespace(**issue())
    report = {"items": [api.row_dict(row)]}
    exported = list(csv.DictReader(io.StringIO(api.history_csv(report).decode("utf-8-sig"))))[0]
    assert exported["Latest Retained Actual (million kWh)"] == ""
    assert exported["Absolute Error (million kWh)"] == ""
    assert exported["Predicted Energy (million kWh)"]
