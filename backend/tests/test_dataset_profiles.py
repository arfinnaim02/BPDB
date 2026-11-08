from datetime import date
from decimal import Decimal

import pytest
from app.api.analytics import METRICS
from app.api.dataset_profiles import build_profiles
from app.api.monitoring import read_session
from app.api.preparation import build_snapshot
from app.api.quality import read_quality
from app.core.config import Settings
from app.core.dataset_policy import CORE_METRICS
from app.db.models import CostObservation
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event
from test_quality import seed


def test_profiles_match_supported_parser_capability_not_a_publication_claim():
    assert CORE_METRICS == {k for k, v in METRICS.items() if v[-1]}
    assert len(CORE_METRICS) == 5
    assert "day_peak_demand" not in CORE_METRICS


def test_empty_history_has_no_invented_training_readiness(session):
    result = build_profiles(read_quality(session))
    assert result["profiles"][0]["start_date"] is None
    assert result["profiles"][1]["start_date"] == "2025-01-01"
    assert result["profiles"][1]["end_date"] is None
    assert all(v["modern_observed_days"] == 0 for v in result["variables"])
    assert all(v["modern_calendar_coverage_percent"] is None for v in result["variables"])
    assert all(p["joint_complete_eligible_dates"] is None for p in result["profiles"])
    assert result["models_fit"] == result["database_writes"] == 0


def test_live_counts_preserve_earlier_modern_values_zero_and_calendar_gaps(session):
    _, older, source = seed(session, date(2024, 1, 1))
    session.add(
        CostObservation(
            version_id=older.id,
            source_id=source.id,
            metric="total_production_cost",
            value=Decimal("12"),
            unit="BDT",
            period="daily",
            fuel="all",
        )
    )
    seed(session, date(2025, 1, 1))
    _, modern, source = seed(session, date(2025, 1, 3))
    session.add(
        CostObservation(
            version_id=modern.id,
            source_id=source.id,
            metric="total_production_cost",
            value=Decimal("0"),
            unit="BDT",
            period="daily",
            fuel="all",
        )
    )
    session.flush()
    statements = []

    def track(_, __, sql, ___, ____, _____):
        statements.append(sql)

    event.listen(session.bind, "before_cursor_execute", track)
    try:
        result = build_profiles(read_quality(session))
    finally:
        event.remove(session.bind, "before_cursor_execute", track)
    assert len(statements) == 2 and all(
        s.lstrip().upper().startswith(("SELECT", "WITH")) for s in statements
    )
    cost = next(v for v in result["variables"] if v["metric"] == "total_production_cost")
    assert cost["earliest_observed_date"] == "2024-01-01"  # Never erase earlier evidence.
    assert cost["full_history_observed_days"] == 2
    assert cost["modern_observed_days"] == 1  # Original zero is an observation.
    assert cost["modern_calendar_days"] == 3
    assert cost["modern_missing_calendar_days"] == 2
    assert cost["modern_calendar_coverage_percent"] == 33.33
    assert cost["model_eligibility"] == "not_approved_by_availability_counts"
    first_id = result["coverage_assessment_id"]
    again = build_profiles(read_quality(session))
    assert again["coverage_assessment_id"] == first_id  # Request timestamp is not identity.
    session.add(
        CostObservation(
            version_id=modern.id,
            source_id=source.id,
            metric="production_cost_per_kwh",
            value=Decimal("1"),
            unit="BDT/kWh",
            period="daily",
            fuel="all",
        )
    )
    session.flush()
    assert build_profiles(read_quality(session))["coverage_assessment_id"] != first_id


@pytest.mark.parametrize(
    "metric",
    [
        "gas_supplied",
        "maximum_temperature",
        "production_cost_per_kwh",
        "total_production_cost",
        "energy_unserved",
        "energy_demand",
        "day_peak_demand",
        "minimum_generation",
    ],
)
def test_unsupported_historical_fields_cannot_receive_experimental_filling(metric):
    with pytest.raises(HTTPException) as exc:
        build_snapshot(
            [],
            metric,
            date(2024, 1, 1),
            date(2024, 1, 15),
            date(2024, 1, 10),
            date(2024, 1, 12),
            "past_week_train_only",
        )
    assert exc.value.status_code == 422
    assert "observed_only" in exc.value.detail


def test_observed_only_modern_pre2025_preview_stays_allowed_and_lossless():
    result = build_snapshot(
        [],
        "gas_supplied",
        date(2024, 1, 1),
        date(2024, 1, 15),
        date(2024, 1, 10),
        date(2024, 1, 12),
        "observed_only",
    )
    assert all(r["prepared_train_value"] is None for r in result["rows"])
    assert result["config"]["rule_version"] == "preparation_v1"


def test_strategy_is_authenticated_and_read_only(session, monkeypatch):
    settings = Settings(_env_file=None, admin_api_key="profiles-test")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    report = read_quality(session)
    monkeypatch.setattr("app.api.dataset_profiles.read_quality", lambda *a, **k: report)
    app.dependency_overrides[read_session] = lambda: None
    try:
        with TestClient(app) as client:
            path = "/api/v1/dataset/research-profiles"
            assert client.get(path).status_code == 401
            response = client.get(path, headers={"X-API-Key": "profiles-test"})
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert len(response.json()["variables"]) == 13
            assert response.json()["database_writes"] == 0
    finally:
        app.dependency_overrides.clear()
