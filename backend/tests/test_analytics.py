from datetime import date
from decimal import Decimal

import pytest
from app.api.analytics import read_analytics, statistics
from app.api.monitoring import read_session
from app.core.config import Settings
from app.db.models import GenerationObservation, ReportVersion
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_quality import seed


def test_empty_analytics_has_null_statistics_and_no_invented_dates(session):
    data = read_analytics(session)
    assert data.points == [] and data.calendar_days == 0
    assert data.start_date is None and data.statistics.mean is None
    assert data.statistics.observed_total is None and data.statistics.observations == 0


def test_mw_averages_never_sum_and_nulls_remain_gaps(session):
    seed(session, date(2026, 1, 1), value=10)
    seed(session, date(2026, 1, 2), value=None)
    seed(session, date(2026, 1, 3), value=20)
    daily = read_analytics(session, resolution="daily")
    assert [point.value for point in daily.points] == ["10", None, "20"]
    assert daily.statistics.mean == "15" and daily.statistics.median == "15"
    assert daily.statistics.sample_stddev == "7.071068"
    assert daily.statistics.observed_total is None
    assert daily.unavailable_metric_dates == 1 and daily.missing_canonical_dates == 0
    monthly = read_analytics(session)
    assert monthly.points[0].value == "15"
    assert monthly.points[0].observed_days == 2 and monthly.points[0].expected_days == 3
    assert not monthly.points[0].complete_period


def test_missing_canonical_date_is_not_a_metric_null_or_zero(session):
    seed(session, date(2026, 1, 1), value=0)
    seed(session, date(2026, 1, 3), value=0)
    data = read_analytics(session, resolution="daily")
    assert [p.value for p in data.points] == ["0", None, "0"]
    assert data.statistics.zero_days == 2 and data.statistics.mean == "0"
    assert data.missing_canonical_dates == 1 and data.unavailable_metric_dates == 0
    assert data.metric_canonical_coverage_percent == 100
    assert data.metric_calendar_coverage_percent == 66.67


def test_energy_sums_available_values_and_flags_partial_period(session):
    for day, value in [(1, "12.34"), (3, "10.66")]:
        _, version, source = seed(session, date(2026, 1, day))
        session.add(
            GenerationObservation(
                version_id=version.id,
                source_id=source.id,
                metric="energy_generated",
                unit="million_kWh",
                period="daily",
                value=Decimal(value),
            )
        )
    session.flush()
    data = read_analytics(session, metric="energy_generated")
    assert data.aggregation == "observed_sum" and data.points[0].value == "23"
    assert data.statistics.mean == "11.5" and data.statistics.observed_total == "23"
    assert data.points[0].coverage_percent == 66.67 and not data.points[0].complete_period


def test_overall_mean_is_weighted_by_observations_not_period_means(session):
    for day, value in [(date(2026, 1, 31), 10), (date(2026, 2, 1), 20), (date(2026, 2, 2), 40)]:
        seed(session, day, value=value)
    data = read_analytics(session)
    assert [p.value for p in data.points] == ["10", "30"]
    assert data.statistics.mean == "23.333333"
    assert read_analytics(session, resolution="yearly").points[0].value == "23.333333"
    assert all(not p.full_period_selected for p in data.points)


def test_complete_leap_month_and_year_window_slice(session):
    for day in range(1, 30):
        seed(session, date(2024, 2, day), value=10)
    monthly = read_analytics(session)
    point = monthly.points[0]
    assert point.expected_days == 29 and point.observed_days == 29
    assert point.full_period_selected and point.complete_period
    yearly = read_analytics(session, resolution="yearly").points[0]
    assert yearly.expected_days == 29 and not yearly.full_period_selected
    assert not yearly.complete_period


def test_date_filter_is_inclusive_and_clips_to_canonical_bounds(session):
    for day in (2, 3, 4):
        seed(session, date(2026, 1, day), value=day)
    data = read_analytics(session, start_date=date(2026, 1, 1), end_date=date(2026, 1, 3))
    assert data.start_date == date(2026, 1, 2) and data.end_date == date(2026, 1, 3)
    assert data.statistics.observations == 2 and data.statistics.mean == "2.5"
    no_overlap = read_analytics(session, start_date=date(2027, 1, 1))
    assert no_overlap.start_date is None and no_overlap.points == []


def test_unavailable_modern_metric_is_not_backfilled(session):
    seed(session, date(2020, 1, 1))
    seed(session, date(2020, 1, 3))
    data = read_analytics(session, metric="energy_demand", resolution="daily")
    assert data.parser_support == "modern_parser_only"
    assert data.statistics.observations == 0 and data.statistics.observed_total is None
    assert data.unavailable_metric_dates == 2
    assert all(p.value is None for p in data.points)


def test_superseded_versions_partial_reports_and_other_grains_are_excluded(session):
    report, _, _ = seed(session, date(2026, 1, 2), value=99)
    current = ReportVersion(
        report_id=report.id,
        version_number=2,
        quality_status="validated",
        parser_version="new",
    )
    session.add(current)
    session.flush()
    report.current_version_id = current.id
    seed(session, date(2020, 1, 1), quality="partial")
    seed(session, date(2027, 1, 1), grain="regional_daily")
    data = read_analytics(session)
    assert data.canonical_dates == 1 and data.statistics.observations == 0
    assert data.earliest_canonical_date == date(2026, 1, 2)


def test_wrong_metric_dimensions_fail_closed(session):
    _, version, source = seed(session, date(2026, 1, 1))
    session.add(
        GenerationObservation(
            version_id=version.id,
            source_id=source.id,
            metric="day_peak_generation",
            value=2,
            unit="MWh",
            period="day_peak",
        )
    )
    session.flush()
    with pytest.raises(HTTPException) as exc:
        read_analytics(session)
    assert exc.value.status_code == 503


def test_missing_measurement_provenance_fails_closed(session):
    _, version, _ = seed(session, date(2026, 1, 1))
    _, _, other_source = seed(session, date(2026, 1, 2))
    session.add(
        GenerationObservation(
            version_id=version.id,
            source_id=other_source.id,
            metric="energy_generated",
            value=3,
            unit="million_kWh",
            period="daily",
        )
    )
    session.flush()
    with pytest.raises(HTTPException) as exc:
        read_analytics(session, metric="energy_generated")
    assert exc.value.status_code == 503


def test_decimal_statistics_do_not_use_binary_float_for_calculation():
    data = statistics([Decimal("999999999999.123456"), Decimal("999999999999.123456")], True)
    assert data.observed_total == "1999999999998.246912"
    assert data.mean == "999999999999.123456" and data.sample_stddev == "0"
    assert statistics([Decimal("1")], False).sample_stddev is None


def test_data_fingerprint_is_resolution_independent_but_filter_sensitive(session):
    seed(session, date(2026, 1, 1))
    seed(session, date(2026, 1, 3))
    monthly = read_analytics(session)
    assert read_analytics(session, resolution="daily").data_fingerprint == monthly.data_fingerprint
    assert (
        read_analytics(session, start_date=date(2026, 1, 3)).data_fingerprint
        != monthly.data_fingerprint
    )


def test_bad_filters_and_excess_daily_points_are_rejected(session, monkeypatch):
    seed(session, date(2026, 1, 1))
    seed(session, date(2026, 1, 3))
    with pytest.raises(HTTPException):
        read_analytics(session, start_date=date(2026, 2, 1), end_date=date(2026, 1, 1))
    monkeypatch.setattr("app.api.analytics.MAX_POINTS", 2)
    with pytest.raises(HTTPException) as exc:
        read_analytics(session, resolution="daily")
    assert exc.value.status_code == 422
    assert len(read_analytics(session).points) == 1


def test_route_auth_enum_validation_and_serialization(session, monkeypatch):
    monkeypatch.setattr(
        "app.main.get_settings",
        lambda: Settings(
            _env_file=None,
            admin_api_key="analytics-test-only",
        ),
    )
    data = read_analytics(session)
    monkeypatch.setattr("app.api.analytics.read_analytics", lambda *_args: data)
    app.dependency_overrides[read_session] = lambda: None
    try:
        with TestClient(app) as client:
            path = "/api/v1/analytics/generation-demand"
            assert client.get(path).status_code == 401
            headers = {"X-API-Key": "analytics-test-only"}
            assert client.get(path + "?metric=unknown", headers=headers).status_code == 422
            assert client.get(path + "?resolution=hourly", headers=headers).status_code == 422
            response = client.get(path, headers=headers)
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["statistics"]["mean"] is None
    finally:
        app.dependency_overrides.pop(read_session, None)
