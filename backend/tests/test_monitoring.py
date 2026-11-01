from datetime import date
from decimal import Decimal

import pytest
from app.api.monitoring import read_master, read_runs, read_session, read_summary
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
from sqlalchemy.exc import OperationalError


def seed(session, day, quality="validated", grain="national_daily"):
    run = IngestionRun(trigger="manual", status="succeeded", statistics={"stage": "test"})
    report = DailyReport(report_date=date(2026, 1, day), dataset_grain=grain)
    session.add_all([run, report])
    session.flush()
    version = ReportVersion(
        report_id=report.id, version_number=1, quality_status=quality, parser_version="test",
    )
    source = SourceDocument(
        original_url=f"https://misc.bpdb.gov.bd/test/{day}/{grain}.pdf", category="page_1",
        sha256="a" * 64, storage_key="private/local/path", original_filename="report.pdf",
        content_type="application/pdf", size_bytes=100, ingestion_run_id=run.id,
    )
    session.add_all([version, source])
    session.flush()
    session.add(VersionSource(version_id=version.id, source_id=source.id))
    measurement = GenerationObservation(
        version_id=version.id, source_id=source.id, metric="day_peak_generation",
        value=Decimal("1234.500000"), unit="MW", period="day_peak", source_page=1,
        raw_text="Day Peak Generation 1234.5 MW",
    )
    session.add(measurement)
    report.current_version_id = version.id
    session.flush()
    return report, version, source, measurement


def test_summary_empty_and_canonical_scope(session):
    empty = read_summary(session)
    assert empty.canonical_dates == 0
    assert empty.earliest_operational_date is None
    assert empty.missing_dates_between_bounds == 0
    seed(session, 1)
    seed(session, 3)
    seed(session, 2, "partial")
    seed(session, 4, grain="regional_daily")
    summary = read_summary(session)
    assert summary.canonical_dates == 2
    assert summary.earliest_operational_date == date(2026, 1, 1)
    assert summary.latest_operational_date == date(2026, 1, 3)
    assert summary.missing_dates_between_bounds == 1


def test_master_pagination_filters_and_lineage(session):
    _, old, _, _ = seed(session, 1)
    _, current, source, _ = seed(session, 3)
    seed(session, 4, "quarantined")
    seed(session, 5, grain="other")
    # Superseded/noncurrent versions must never be returned.
    session.add(ReportVersion(
        report_id=old.report_id, version_number=2, quality_status="validated",
        parser_version="not-current",
    ))
    session.flush()
    page = read_master(session, page_size=1)
    assert (page.total_dates, page.total_pages) == (2, 2)
    day = page.items[0]
    assert day.report_version_id == current.id
    assert day.operational_date == date(2026, 1, 3)
    assert day.available_at is None
    assert day.sources[0].sha256 == "a" * 64
    assert day.measurements[0].source_id == source.id
    assert day.measurements[0].value == "1234.500000"
    assert day.measurements[0].unit == "MW"
    assert "private/local/path" not in page.model_dump_json()
    assert read_master(session, page=2, page_size=1).items[0].operational_date == date(2026, 1, 1)
    filtered = read_master(session, date(2026, 1, 3), date(2026, 1, 3))
    assert filtered.total_dates == 1
    assert read_master(session, page=99).items == []


def test_master_preserves_null_dimensions_and_national_scope(session):
    _, version, source, _ = seed(session, 1)
    session.add_all([
        CostObservation(
            version_id=version.id, source_id=source.id, metric="cost", value=None,
            unit="BDT", fuel="gas", period="daily", source_page=1,
        ),
        GenerationObservation(
            version_id=version.id, source_id=source.id, metric="generation",
            value=999, unit="MW", zone="Dhaka", source_page=1,
        ),
    ])
    session.flush()
    values = read_master(session).items[0].measurements
    assert len(values) == 2
    assert values[0].metric == "cost"
    assert values[0].value is None and values[0].fuel == "gas"


def test_master_rejects_broken_source_links(session):
    _, version, _, _ = seed(session, 1)
    _, _, other_source, _ = seed(session, 2)
    session.add(CostObservation(
        version_id=version.id, source_id=other_source.id, metric="cost", value=1, unit="BDT",
    ))
    session.flush()
    with pytest.raises(HTTPException) as exc:
        read_master(session)
    assert exc.value.status_code == 503


def test_master_rejects_duplicate_metric_across_tables(session):
    _, version, source, _ = seed(session, 1)
    session.add(DemandObservation(
        version_id=version.id, source_id=source.id, metric="day_peak_generation",
        period="day_peak", value=1, unit="MW",
    ))
    session.flush()
    with pytest.raises(HTTPException) as exc:
        read_master(session)
    assert exc.value.status_code == 503


def test_master_date_validation(session):
    with pytest.raises(HTTPException) as exc:
        read_master(session, date(2026, 2, 1), date(2026, 1, 1))
    assert exc.value.status_code == 422


def test_history_filters_and_redacts(session):
    session.add_all([
        IngestionRun(trigger="scheduled", status="partial", statistics={
            "stage": "daily_worker", "cached": 4, "promoted": True,
            "private_debug": "secret", "archive_scan": {
                "pages_scanned": 3, "page_failures": [{"private_url": "hidden"}],
            },
        }),
        IngestionRun(trigger="manual", status="succeeded", statistics={"stage": "other"}),
    ])
    session.flush()
    result = read_runs(session, 20)
    assert len(result.items) == 1
    run = result.items[0]
    assert run.status == "partial" and run.trigger == "scheduled"
    assert run.counters["cached"] == 4 and run.counters["promoted"] is None
    assert run.pages_scanned == 3 and run.archive_page_failures == 1
    assert run.drive_checkpoint_status == "not_recorded_in_ingestion_run"
    assert "secret" not in result.model_dump_json()
    assert "hidden" not in result.model_dump_json()


def test_routes_auth_bounds_and_registration(monkeypatch):
    settings = Settings(_env_file=None, admin_api_key="test-only")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    app.dependency_overrides[read_session] = lambda: None
    try:
        with TestClient(app) as client:
            for path in ("/dataset/summary", "/dataset/daily", "/collection/runs"):
                assert client.get("/api/v1" + path).status_code == 401
                wrong = client.get("/api/v1" + path, headers={"X-API-Key": "wrong"})
                assert wrong.status_code == 401
            for suffix in ("dataset/daily?page_size=101", "dataset/daily?page=0",
                           "dataset/daily?start_date=invalid", "collection/runs?limit=101"):
                assert client.get(
                    "/api/v1/" + suffix, headers={"X-API-Key": "test-only"},
                ).status_code == 422
    finally:
        app.dependency_overrides.pop(read_session, None)


def test_endpoint_serialization_and_cache_headers(monkeypatch):
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(
        _env_file=None, admin_api_key="test-only",
    ))
    app.dependency_overrides[read_session] = lambda: None
    monkeypatch.setattr("app.api.monitoring.read_summary", lambda _: {
        "canonical_dates": 0, "earliest_operational_date": None,
        "latest_operational_date": None, "missing_dates_between_bounds": 0,
        "generated_at": "2026-11-01T00:00:00Z",
    })
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/dataset/summary", headers={"X-API-Key": "test-only"})
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["canonical_dates"] == 0
    finally:
        app.dependency_overrides.pop(read_session, None)


def test_database_failure_does_not_expose_credentials(monkeypatch):
    def broken():
        raise OperationalError("secret connection", {}, Exception("password"))
    monkeypatch.setattr("app.api.monitoring.session_factory", broken)
    with pytest.raises(HTTPException) as exc:
        next(read_session())
    assert exc.value.status_code == 503
    assert "password" not in exc.value.detail


def test_master_refuses_empty_canonical_measurements(session):
    _, _, _, measurement = seed(session, 1)
    session.delete(measurement)
    session.flush()
    with pytest.raises(HTTPException) as exc:
        read_master(session)
    assert exc.value.status_code == 503


def test_history_order_and_limit(session):
    from datetime import datetime, timezone

    for day in (1, 2, 3):
        session.add(IngestionRun(
            trigger="manual", status="succeeded", statistics={"stage": "daily_worker"},
            created_at=datetime(2026, 1, day, tzinfo=timezone.utc),
        ))
    session.flush()
    history = read_runs(session, 2)
    assert len(history.items) == 2
    assert [item.started_at.day for item in history.items] == [3, 2]
