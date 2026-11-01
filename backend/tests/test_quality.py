from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from app.api.monitoring import read_session
from app.api.quality import read_quality
from app.core.config import Settings
from app.db.models import (
    CostObservation,
    DailyReport,
    DemandObservation,
    GenerationObservation,
    IngestionRun,
    ReportVersion,
    SourceDocument,
    VersionSource,
)
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event


def seed(session, day, value=1, quality="validated", grain="national_daily", row=True):
    run = IngestionRun(trigger="manual", status="succeeded")
    report = DailyReport(report_date=day, dataset_grain=grain)
    session.add_all([run, report])
    session.flush()
    version = ReportVersion(
        report_id=report.id, version_number=1, quality_status=quality,
        parser_version="quality-test",
    )
    source = SourceDocument(
        original_url=f"https://misc.bpdb.gov.bd/test/{uuid4()}.pdf", category="page_1",
        sha256="a" * 64, storage_key="private-path", original_filename="report.pdf",
        content_type="application/pdf", size_bytes=100, ingestion_run_id=run.id,
    )
    session.add_all([version, source])
    session.flush()
    session.add(VersionSource(version_id=version.id, source_id=source.id))
    if row:
        session.add(GenerationObservation(
            version_id=version.id, source_id=source.id, metric="day_peak_generation",
            value=value, unit="MW", period="day_peak",
        ))
    report.current_version_id = version.id
    session.flush()
    return report, version, source


def generation(result):
    return next(m for m in result.metrics if m.metric == "day_peak_generation" and m.unit == "MW")


def test_empty_history_has_no_invented_bounds(session):
    result = read_quality(session)
    assert result.canonical_dates == 0 and result.calendar_days == 0
    assert result.earliest_operational_date is None and result.latest_operational_date is None
    assert result.calendar_coverage_percent is None
    assert result.gaps.total_ranges == 0 and result.gaps.items == []
    assert result.years == [] and len(result.metrics) == 13
    assert all(m.coverage_percent is None and m.by_year == [] for m in result.metrics)


def test_full_history_exceeds_100_dates_and_uses_two_queries(session):
    start = date(2020, 1, 1)
    for i in range(105):
        seed(session, start + timedelta(days=i), value=Decimal(i) if i % 2 == 0 else None)
    queries = []

    def track(_connection, _cursor, statement, *_args):
        queries.append(statement)

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", track)
    try:
        result = read_quality(session)
    finally:
        event.remove(engine, "before_cursor_execute", track)
    metric = generation(result)
    assert result.canonical_dates == 105 and result.calendar_days == 105
    assert result.missing_dates == 0 and result.calendar_coverage_percent == 100
    assert metric.non_null_dates == 53 and metric.missing_or_null_dates == 52
    assert metric.zero_dates == 1 and metric.coverage_percent == 50.48
    assert metric.earliest_value_date == start
    assert metric.latest_value_date == start + timedelta(days=104)
    assert len(queries) == 2 and "raw_text" not in " ".join(queries)


def test_null_absent_and_zero_are_distinguished(session):
    seed(session, date(2026, 1, 1), value=0)
    seed(session, date(2026, 1, 2), value=None)
    seed(session, date(2026, 1, 3), row=False)
    result = read_quality(session)
    metric = generation(result)
    assert metric.non_null_dates == 1 and metric.zero_dates == 1
    assert metric.missing_or_null_dates == 2 and metric.coverage_percent == 33.33
    assert metric.by_year[0].non_null_dates == 1 and result.missing_dates == 0


def test_leap_day_gaps_are_exact_and_paginated(session):
    for day in [date(2024, 2, 28), date(2024, 3, 1), date(2024, 3, 4)]:
        seed(session, day)
    result = read_quality(session, gap_page=1, gap_page_size=1)
    assert result.calendar_days == 6 and result.missing_dates == 3
    assert result.calendar_coverage_percent == 50
    assert result.gaps.total_ranges == 2 and result.gaps.total_pages == 2
    assert result.gaps.items[0].start_date == date(2024, 2, 29)
    assert result.gaps.items[0].days == 1
    second = read_quality(session, gap_page=2, gap_page_size=1)
    assert second.gaps.items[0].start_date == date(2024, 3, 2)
    assert second.gaps.items[0].end_date == date(2024, 3, 3)
    assert second.gaps.items[0].days == 2
    assert second.gaps.items[0].source_report_status == "not_assessed"
    assert read_quality(session, gap_page=3, gap_page_size=1).gaps.items == []


def test_year_boundary_clips_calendar_denominator(session):
    seed(session, date(2019, 12, 30))
    seed(session, date(2020, 1, 2))
    result = read_quality(session)
    assert [(y.year, y.calendar_days, y.canonical_dates, y.missing_dates)
            for y in result.years] == [(2019, 2, 1, 1), (2020, 2, 1, 1)]
    assert result.gaps.items[0].start_date == date(2019, 12, 31)
    assert result.gaps.items[0].end_date == date(2020, 1, 1)
    assert generation(result).coverage_percent == 100
    assert result.calendar_coverage_percent == 50


def test_entire_missing_year_is_visible(session):
    seed(session, date(2020, 12, 31))
    seed(session, date(2022, 1, 1))
    result = read_quality(session)
    year = result.years[1]
    assert year.year == 2021 and year.calendar_days == 365
    assert year.canonical_dates == 0 and year.missing_dates == 365
    assert year.coverage_percent == 0
    assert generation(result).by_year[1].coverage_percent is None
    assert result.gaps.items[0].days == 365


def test_only_current_validated_national_versions_count(session):
    report, _, _ = seed(session, date(2020, 1, 2))
    new = ReportVersion(
        report_id=report.id, version_number=2, quality_status="validated", parser_version="new",
    )
    session.add(new)
    session.flush()
    report.current_version_id = new.id
    seed(session, date(2019, 1, 1), quality="partial")
    seed(session, date(2021, 1, 1), quality="quarantined")
    seed(session, date(2022, 1, 1), grain="regional_daily")
    result = read_quality(session)
    assert result.canonical_dates == 1 and result.calendar_days == 1
    assert result.earliest_operational_date == date(2020, 1, 2)
    assert generation(result).non_null_dates == 0


def test_dimensions_are_preserved_and_distinct_dates_prevent_inflation(session):
    _, version, source = seed(session, date(2020, 1, 1))
    common = {"version_id": version.id, "source_id": source.id}
    session.add_all([
        GenerationObservation(**common, metric="day_peak_generation", value=2,
                              unit="MWh", period="daily"),
        GenerationObservation(**common, metric="day_peak_generation", value=9,
                              unit="MW", period="day_peak", zone="Dhaka"),
        CostObservation(**common, metric="total_production_cost", value=3,
                        unit="BDT", period="daily", fuel="coal"),
        CostObservation(**common, metric="total_production_cost", value=None,
                        unit="BDT", period="daily", fuel="all"),
        DemandObservation(**common, metric="day_peak_generation", value=2,
                          unit="MW", period="day_peak"),
    ])
    session.flush()
    result = read_quality(session)
    assert generation(result).non_null_dates == 1
    assert generation(result).coverage_percent == 100
    assert next(m for m in result.metrics if m.unit == "MWh").non_null_dates == 1
    costs = {m.fuel: m for m in result.metrics if m.metric == "total_production_cost"}
    assert costs["coal"].non_null_dates == 1 and costs["all"].non_null_dates == 0


def test_auth_and_pagination_validation(monkeypatch):
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(
        _env_file=None, admin_api_key="quality-test-only",
    ))
    app.dependency_overrides[read_session] = lambda: None
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/dataset/quality").status_code == 401
            headers = {"X-API-Key": "quality-test-only"}
            for query in ["gap_page=0", "gap_page=100001", "gap_page_size=101"]:
                response = client.get("/api/v1/dataset/quality?" + query, headers=headers)
                assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(read_session, None)
    with pytest.raises(HTTPException):
        read_quality(None, gap_page_size=101)


def test_endpoint_serializes_with_no_store(monkeypatch, session):
    data = read_quality(session)
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(
        _env_file=None, admin_api_key="quality-test-only",
    ))
    monkeypatch.setattr("app.api.quality.read_quality", lambda *_args: data)
    app.dependency_overrides[read_session] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/dataset/quality", headers={"X-API-Key": "quality-test-only"},
            )
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["canonical_dates"] == 0
            assert "private-path" not in response.text
    finally:
        app.dependency_overrides.pop(read_session, None)
