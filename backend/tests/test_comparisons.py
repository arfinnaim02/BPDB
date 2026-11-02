import calendar
from datetime import date
from decimal import Decimal

import pytest
from app.api.comparisons import read_comparisons
from app.api.monitoring import read_session
from app.core.config import Settings
from app.db.models import DemandObservation, GenerationObservation
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_quality import seed


def day(session, when, value=10, generation=None, demand=None, energy=None, **kwargs):
    report, version, source = seed(session, when, value=value, **kwargs)
    for metric, table, amount, unit, period in (
        ("evening_peak_generation", GenerationObservation, generation, "MW", "evening_peak"),
        ("evening_peak_demand", DemandObservation, demand, "MW", "evening_peak"),
        ("energy_generated", GenerationObservation, energy, "million_kWh", "daily"),
    ):
        if amount is not None:
            session.add(
                table(
                    version_id=version.id,
                    source_id=source.id,
                    metric=metric,
                    value=Decimal(amount),
                    unit=unit,
                    period=period,
                )
            )
    session.flush()
    return report, version, source


def month(session, year, number, value, energy=None):
    for n in range(1, calendar.monthrange(year, number)[1] + 1):
        day(session, date(year, number, n), value=value, energy=energy)


def test_empty_comparisons_do_not_invent_years_or_differences(session):
    result = read_comparisons(session)
    assert result.calendar_days == 0 and result.paired_days == 0
    assert result.selected_years == result.monthly == result.annual == result.paired_points == []
    assert result.paired_difference_mean is None


def test_pair_means_use_identical_nonnull_days_not_independent_samples(session):
    day(session, date(2026, 1, 1), generation=10, demand=15)
    day(session, date(2026, 1, 2), generation=100)
    day(session, date(2026, 1, 3), demand=30)
    result = read_comparisons(session)
    p = result.paired_points[0]
    assert p.generation_mean == "10" and p.demand_mean == "15" and p.difference_mean == "5"
    assert p.paired_days == result.paired_days == 1 and p.expected_days == 3
    assert result.paired_coverage_percent == 33.33 and not p.complete_period
    assert result.demand_above_generation_days == 1


def test_daily_calendar_gap_and_negative_difference_are_preserved(session):
    day(session, date(2026, 1, 1), generation="10.123456", demand="10.223456")
    day(session, date(2026, 1, 3), generation=12, demand=10)
    result = read_comparisons(session, resolution="daily")
    assert [p.difference_mean for p in result.paired_points] == ["0.1", None, "-2"]
    assert [p.paired_days for p in result.paired_points] == [1, 0, 1]
    assert result.paired_difference_mean == "-0.95"
    assert result.demand_above_generation_days == result.generation_above_demand_days == 1


def test_complete_month_changes_and_zero_baseline(session):
    month(session, 2025, 1, 0)
    month(session, 2025, 2, 20)
    month(session, 2025, 3, 30)
    result = read_comparisons(session)
    jan, feb, mar = result.monthly
    assert jan.complete_period and feb.complete_period and mar.complete_period
    assert jan.mom_status == "baseline_outside_window"
    assert feb.mom_status == "zero_baseline" and feb.mom_percent is None
    assert mar.mom_percent == "50" and mar.mom_status == "comparable_complete_months"
    assert mar.yoy_percent is None


def test_yoy_uses_calendar_lag_even_when_other_months_missing(session):
    month(session, 2025, 1, 10)
    month(session, 2026, 1, 20)
    result = read_comparisons(session, years=[2026])
    assert result.selected_years == [2026] and len(result.monthly) == 1
    jan = result.monthly[0]
    assert jan.yoy_percent == "100" and jan.yoy_status == "comparable_complete_months"
    assert jan.mom_percent is None and jan.mom_status == "baseline_month_incomplete"
    # A displayed-year selection does not remove earlier dates from the paired timeline.
    assert result.paired_points[0].label == "2025-01"


def test_incomplete_baseline_withholds_change_and_never_fills_values(session):
    month(session, 2025, 1, 10)
    month(session, 2025, 2, 20)
    row = session.scalar(
        select(GenerationObservation)
        .where(
            GenerationObservation.metric == "day_peak_generation",
        )
        .limit(1)
    )
    row.value = None
    session.flush()
    result = read_comparisons(session)
    assert result.monthly[0].observed_days == 30
    assert result.monthly[1].mom_percent is None
    assert result.monthly[1].mom_status == "baseline_month_incomplete"


def test_sliced_months_and_no_overlap(session):
    month(session, 2026, 1, 10)
    result = read_comparisons(session, start_date=date(2026, 1, 2), end_date=date(2026, 1, 30))
    p = result.monthly[0]
    assert p.expected_days == p.observed_days == 29 and not p.full_period_selected
    assert not p.complete_period and p.mom_status == "current_month_incomplete"
    empty = read_comparisons(session, start_date=date(2027, 1, 1))
    assert empty.start_date is None and not empty.monthly and empty.paired_days == 0


def test_energy_sums_and_annual_mw_weighting(session):
    month(session, 2026, 1, 10, energy="2")
    month(session, 2026, 2, 20, energy="3")
    energy = read_comparisons(session, metric="energy_generated")
    assert [p.value for p in energy.monthly] == ["62", "84"]
    assert energy.monthly[1].mom_percent == "35.483871"  # Observed monthly sums, not daily means.
    assert energy.annual[0].value == "146" and not energy.annual[0].complete_period
    mw = read_comparisons(session)
    assert mw.annual[0].value == "14.745763"  # (31*10 + 28*20)/59; not a mean of month means.


def test_leap_month_and_unavailable_day_demand(session):
    month(session, 2024, 2, 10)
    result = read_comparisons(session, peak="day")
    assert result.monthly[0].expected_days == 29 and result.monthly[0].complete_period
    assert result.paired_days == 0 and result.paired_difference_mean is None
    assert all(p.demand_mean is None and p.generation_mean is None for p in result.paired_points)


def test_null_and_real_zero_are_different_in_pair_counts(session):
    day(session, date(2026, 1, 1), generation=0, demand=0)
    day(session, date(2026, 1, 2), generation=0)
    result = read_comparisons(session, resolution="daily")
    assert result.paired_days == 1 and result.equal_days == 1
    assert result.paired_points[0].difference_mean == "0"
    assert result.paired_points[1].difference_mean is None
    assert result.generation_energy_review_dates == 2


def test_only_current_validated_national_records_and_read_only(session):
    day(session, date(2026, 1, 1), generation=10, demand=11)
    day(session, date(2026, 1, 2), generation=50, demand=1, quality="quarantined")
    day(session, date(2026, 1, 3), generation=50, demand=1, grain="regional_daily")
    report, _, _ = day(session, date(2026, 1, 4), generation=50, demand=1)
    report.current_version_id = None
    session.flush()
    result = read_comparisons(session)
    assert result.canonical_dates == result.paired_days == 1
    assert result.paired_difference_mean == "1"
    assert not session.new and not session.dirty and not session.deleted


def test_integrity_and_input_guards(session):
    _, version, _ = day(session, date(2026, 1, 1), generation=10, demand=20)
    row = session.scalar(
        select(DemandObservation).where(DemandObservation.version_id == version.id)
    )
    row.unit = "MWh"
    session.flush()
    with pytest.raises(HTTPException) as error:
        read_comparisons(session)
    assert error.value.status_code == 503
    for kwargs in (
        {"years": list(range(2000, 2009))},
        {"years": [1800]},
        {"peak": "hour"},
        {"resolution": "minute"},
        {"start_date": date(2026, 2, 1), "end_date": date(2026, 1, 1)},
    ):
        with pytest.raises(HTTPException):
            read_comparisons(session, **kwargs)


def test_year_defaults_deduplicate_and_fingerprint_tracks_inputs(session):
    for year in (2020, 2021, 2022, 2023):
        day(session, date(year, 1, 1), generation=10, demand=20)
    result = read_comparisons(session)
    assert result.selected_years == [2021, 2022, 2023]
    other = read_comparisons(session, years=[2020, 2020, 2023])
    assert other.selected_years == [2020, 2023]
    assert result.data_fingerprint != other.data_fingerprint
    assert result.data_fingerprint == read_comparisons(session).data_fingerprint


def test_comparison_route_auth_validation_and_cache(monkeypatch, session):
    snapshot = read_comparisons(session)
    settings = Settings(_env_file=None, admin_api_key="comparison-test-only")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.comparisons.read_comparisons", lambda *_: snapshot)
    app.dependency_overrides[read_session] = lambda: None
    headers = {"X-API-Key": "comparison-test-only"}
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/analytics/comparisons").status_code == 401
            assert (
                client.get("/api/v1/analytics/comparisons?peak=bad", headers=headers).status_code
                == 422
            )
            assert (
                client.get(
                    "/api/v1/analytics/comparisons?year=2020&year=2021", headers=headers
                ).status_code
                == 200
            )
            response = client.get("/api/v1/analytics/comparisons", headers=headers)
            assert response.headers["cache-control"] == "no-store"
    finally:
        app.dependency_overrides.clear()
