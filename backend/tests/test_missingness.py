from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.api.missingness import read_missingness
from app.api.monitoring import read_session
from app.core.config import Settings
from app.db.models import CostObservation, GenerationObservation, VersionSource
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_quality import seed


def energy(session, day, value, **kwargs):
    report, version, source = seed(session, day, value=100, **kwargs)
    session.add(
        GenerationObservation(
            version_id=version.id,
            source_id=source.id,
            metric="energy_generated",
            value=None if value is None else Decimal(value),
            unit="million_kWh",
            period="daily",
        )
    )
    session.flush()
    return report, version, source


def test_empty_assessment_has_no_invented_dates_or_observed_window(session):
    result = read_missingness(session)
    assert result.start_date is None and result.calendar_days == result.canonical_dates == 0
    assert len(result.metrics) == 13 and result.gaps == result.months == []
    assert result.selected.before_first_value_days is None
    assert result.selected.internal_missing_days is None
    assert result.selected.calendar_coverage_percent is None


def test_missing_date_absent_row_null_and_zero_are_disjoint(session):
    energy(session, date(2026, 1, 1), "0")
    energy(session, date(2026, 1, 2), None)
    seed(session, date(2026, 1, 4))  # Energy row absent.
    energy(session, date(2026, 1, 5), "10")
    result = read_missingness(session)
    s = result.selected
    assert result.calendar_days == 5 and result.canonical_dates == 4
    assert s.observed_days == 2 and s.zero_days == 1 and s.unavailable_days == 3
    assert s.missing_canonical_days == s.absent_field_days == s.explicit_null_days == 1
    assert s.internal_missing_days == s.longest_internal_missing_run == 3
    assert s.before_first_value_days == s.after_last_value_days == 0
    gap = result.gaps[0]
    assert gap.position == "internal" and gap.days == 3 and gap.source_cause == "not_assessed"
    assert gap.days == gap.missing_canonical_days + gap.absent_field_days + gap.explicit_null_days
    assert sum(b.days for b in result.run_bins) == s.unavailable_days
    assert result.months[0].zero_days == 1


def test_boundary_unavailability_is_not_called_structural_absence(session):
    seed(session, date(2020, 1, 1))
    energy(session, date(2020, 1, 3), "1")  # Suspicious but still genuinely stored/non-null.
    seed(session, date(2020, 1, 5))
    result = read_missingness(session)
    assert result.selected.observed_days == 1
    assert result.selected.before_first_value_days == result.selected.after_last_value_days == 2
    assert result.selected.internal_missing_days == 0
    assert [r.position for r in result.gaps] == ["leading", "trailing"]
    assert all(r.source_cause == "not_assessed" for r in result.gaps)


def test_never_observed_metric_has_no_fake_internal_window(session):
    seed(session, date(2020, 1, 1))
    seed(session, date(2020, 1, 3))
    result = read_missingness(session, metric="day_peak_demand")
    s = result.selected
    assert s.observed_days == 0 and s.unavailable_days == 3
    assert s.first_value_date is s.last_value_date is None
    assert s.before_first_value_days is s.after_last_value_days is s.internal_missing_days is None
    assert s.longest_internal_missing_run is None and s.parser_support == "modern_parser_only"
    assert result.gaps[0].position == "no_observed_window"


def test_full_leap_month_and_slice_have_different_completeness(session):
    for n in range(1, 30):
        energy(session, date(2024, 2, n), "0")
    whole = read_missingness(session)
    assert whole.selected.complete_months == whole.selected.whole_months_selected == 1
    assert whole.months[0].calendar_days == whole.months[0].observed_days == 29
    assert whole.months[0].zero_days == 29 and whole.months[0].all_calendar_days_observed
    assert whole.selected.longest_observed_streak == whole.selected.latest_observed_streak == 29
    sliced = read_missingness(session, start_date=date(2024, 2, 2), end_date=date(2024, 2, 28))
    assert sliced.selected.complete_months == sliced.selected.whole_months_selected == 0
    assert sliced.selected.sliced_months == 1
    assert sliced.months[0].status == "window_slice" and sliced.months[0].observed_days == 27


def test_complete_month_streak_resets_on_an_incomplete_month(session):
    for offset in range(121):  # Jan-Apr 2024, including leap February.
        when = date(2024, 1, 1) + timedelta(days=offset)
        energy(session, when, None if when == date(2024, 2, 2) else "2")
    result = read_missingness(session)
    s = result.selected
    assert s.whole_months_selected == 4 and s.complete_months == 3
    assert s.incomplete_whole_months == 1 and s.longest_complete_month_streak == 2
    assert [m.label for m in result.months] == ["2024-04", "2024-03", "2024-02", "2024-01"]


def test_long_run_and_whole_unobserved_month_are_retained(session):
    energy(session, date(2024, 1, 1), "1")
    energy(session, date(2024, 3, 1), "2")
    result = read_missingness(session)
    assert result.selected.longest_missing_run == 59
    assert result.run_bins[-1].runs == 1 and result.run_bins[-1].days == 59
    feb = next(m for m in result.months if m.label == "2024-02")
    assert feb.calendar_days == 29 and feb.observed_days == 0
    assert feb.whole_calendar_month_selected and not feb.all_calendar_days_observed
    assert feb.status == "no_observations"


def test_window_entirely_inside_calendar_gap_is_assessed(session):
    energy(session, date(2026, 1, 1), "1")
    energy(session, date(2026, 1, 5), "2")
    result = read_missingness(session, start_date=date(2026, 1, 2), end_date=date(2026, 1, 4))
    assert result.calendar_days == result.missing_canonical_days == 3
    assert result.canonical_dates == 0 and result.gaps[0].days == 3
    assert result.start_date == date(2026, 1, 2)
    outside = read_missingness(session, start_date=date(2027, 1, 1))
    assert outside.start_date is None and outside.calendar_days == 0 and outside.gaps == []


def test_all_metric_dimensions_include_cost_gas_and_temperature(session):
    _, version, source = energy(session, date(2026, 1, 1), "1")
    session.add(
        CostObservation(
            version_id=version.id,
            source_id=source.id,
            metric="total_production_cost",
            unit="BDT",
            period="daily",
            fuel="all",
            value=100,
        )
    )
    session.flush()
    result = read_missingness(session, metric="total_production_cost")
    assert result.selected.observed_days == 1 and result.selected.unit == "BDT"
    assert result.selected.fuel == "all"
    assert {s.metric for s in result.metrics} >= {
        "maximum_temperature",
        "gas_supplied",
        "production_cost_per_kwh",
    }


def test_invalid_dimensions_or_provenance_are_not_counted_as_missing(session):
    _, version, _ = energy(session, date(2026, 1, 1), "1")
    row = session.scalar(
        select(GenerationObservation).where(
            GenerationObservation.version_id == version.id,
            GenerationObservation.metric == "energy_generated",
        )
    )
    row.unit = "MWh"
    session.flush()
    with pytest.raises(HTTPException) as error:
        read_missingness(session)
    assert error.value.status_code == 503
    row.unit = "million_kWh"
    link = session.scalar(select(VersionSource).where(VersionSource.version_id == version.id))
    session.delete(link)
    session.flush()
    with pytest.raises(HTTPException):
        read_missingness(session)


def test_wrong_fuel_and_wrong_storage_table_are_rejected(session):
    _, version, source = energy(session, date(2026, 1, 1), "1")
    cost = CostObservation(
        version_id=version.id,
        source_id=source.id,
        metric="total_production_cost",
        value=10,
        unit="BDT",
        period="daily",
        fuel="gas",
    )
    session.add(cost)
    session.flush()
    with pytest.raises(HTTPException):
        read_missingness(session)
    session.delete(cost)
    session.add(
        GenerationObservation(
            version_id=version.id,
            source_id=source.id,
            metric="maximum_temperature",
            value=30,
            unit="degC",
            period="daily_maximum",
        )
    )
    session.flush()
    with pytest.raises(HTTPException):
        read_missingness(session)


def test_current_validated_national_scope_and_no_writes(session):
    energy(session, date(2026, 1, 1), "1")
    energy(session, date(2026, 1, 2), "2", quality="quarantined")
    energy(session, date(2026, 1, 3), "3", grain="regional_daily")
    report, _, _ = energy(session, date(2026, 1, 4), "4")
    report.current_version_id = None
    session.flush()
    result = read_missingness(session)
    assert result.calendar_days == result.canonical_dates == result.selected.observed_days == 1
    assert not session.new and not session.dirty and not session.deleted


def test_gap_month_pagination_and_fingerprint_scope(session):
    for i in range(50):
        seed(session, date(2026, 1, 1) + timedelta(days=i), value=None if i % 2 else 0)
    first = read_missingness(session, metric="day_peak_generation")
    second = read_missingness(session, metric="day_peak_generation", gap_page=2)
    assert first.selected.missing_runs == 25 and len(first.gaps) == 20 and len(second.gaps) == 5
    assert first.data_fingerprint == second.data_fingerprint
    assert (
        first.data_fingerprint
        == read_missingness(session, metric="energy_generated").data_fingerprint
    )
    assert sum(b.runs for b in first.run_bins) == 25


def test_month_page_order_and_real_value_changes_invalidate_fingerprint(session):
    _, version, _ = energy(session, date(2020, 1, 1), "1")
    energy(session, date(2023, 1, 1), "2")
    result = read_missingness(session, month_page=2)
    assert result.month_total_pages == 2 and result.months[0].label == "2021-01"
    assert result.months[-1].label == "2020-01"
    row = session.scalar(
        select(GenerationObservation).where(
            GenerationObservation.version_id == version.id,
            GenerationObservation.metric == "energy_generated",
        )
    )
    row.value = Decimal(3)
    session.flush()
    assert result.data_fingerprint != read_missingness(session).data_fingerprint


def test_bounds_and_invalid_parameters(session):
    energy(session, date(1900, 1, 1), "1")
    energy(session, date(2026, 1, 1), "2")
    with pytest.raises(HTTPException):
        read_missingness(session)
    assert read_missingness(session, start_date=date(2026, 1, 1)).calendar_days == 1
    for kwargs in (
        {"metric": "unknown"},
        {"gap_page_size": 51},
        {"gap_page": 0},
        {"month_page": 0},
        {"start_date": date(2026, 2, 1), "end_date": date(2026, 1, 1)},
    ):
        with pytest.raises(HTTPException):
            read_missingness(session, **kwargs)


def test_missingness_auth_and_no_store(monkeypatch, session):
    snapshot = read_missingness(session)
    settings = Settings(_env_file=None, admin_api_key="missing-test-only")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.missingness.read_missingness", lambda *_: snapshot)
    app.dependency_overrides[read_session] = lambda: None
    headers = {"X-API-Key": "missing-test-only"}
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/dataset/missingness").status_code == 401
            assert (
                client.get(
                    "/api/v1/dataset/missingness?metric=unknown", headers=headers
                ).status_code
                == 422
            )
            assert (
                client.get(
                    "/api/v1/dataset/missingness?gap_page_size=51", headers=headers
                ).status_code
                == 422
            )
            result = client.get("/api/v1/dataset/missingness", headers=headers)
            assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
    finally:
        app.dependency_overrides.clear()
