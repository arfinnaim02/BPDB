"""Read-only views of canonical data and daily worker history."""

from collections.abc import Iterator
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import and_, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import (
    CostObservation,
    DailyReport,
    DemandObservation,
    EnvironmentObservation,
    FuelObservation,
    GenerationObservation,
    IngestionRun,
    LoadSheddingObservation,
    ReportVersion,
    SourceDocument,
    VersionSource,
)
from app.db.session import session_factory

router = APIRouter(prefix="/api/v1", tags=["Dataset and collection"])
COUNTERS = (
    "downloaded", "cached", "download_failed", "processing_failed", "raw_only",
    "already_linked", "held_quarantine", "quarantined", "promoted",
    "review_required", "export_failed",
)
TABLES = (
    GenerationObservation, DemandObservation, FuelObservation, CostObservation,
    EnvironmentObservation, LoadSheddingObservation,
)


def read_session() -> Iterator[Session]:
    try:
        with session_factory()() as session:
            if session.get_bind().dialect.name == "postgresql":
                session.execute(text(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                ))
                session.execute(text("SET LOCAL statement_timeout = '15000'"))
            yield session
    except (SQLAlchemyError, RuntimeError):
        raise HTTPException(503, "Dataset service unavailable") from None


Database = Annotated[Session, Depends(read_session)]


def canonical_query():
    return select(
        DailyReport.report_date.label("operational_date"),
        ReportVersion.id.label("version_id"),
        ReportVersion.parser_version,
        ReportVersion.available_at,
    ).join(ReportVersion, and_(
        DailyReport.current_version_id == ReportVersion.id,
        DailyReport.id == ReportVersion.report_id,
    )).where(
        DailyReport.dataset_grain == "national_daily",
        ReportVersion.quality_status == "validated",
    )


class DatasetSummary(BaseModel):
    scope: str = "Supported canonical Page 1 national metrics"
    canonical_dates: int
    earliest_operational_date: date | None
    latest_operational_date: date | None
    missing_dates_between_bounds: int
    generated_at: datetime
    limitation: str = "Missing canonical dates do not prove missing official reports."


def read_summary(session: Session) -> DatasetSummary:
    eligible = canonical_query().subquery()
    count, first, last = session.execute(select(
        func.count(), func.min(eligible.c.operational_date),
        func.max(eligible.c.operational_date),
    ).select_from(eligible)).one()
    return DatasetSummary(
        canonical_dates=count, earliest_operational_date=first,
        latest_operational_date=last,
        missing_dates_between_bounds=(last - first).days + 1 - count if count else 0,
        generated_at=datetime.now(timezone.utc),
    )


class WorkerRun(BaseModel):
    id: str
    status: str
    trigger: str
    started_at: datetime
    finished_at: datetime | None
    counters: dict[str, int | None]
    pages_scanned: int | None
    archive_page_failures: int | None
    drive_checkpoint_status: str = "not_recorded_in_ingestion_run"


class WorkerHistory(BaseModel):
    items: list[WorkerRun]
    limit: int
    scope: str = "Daily worker runs only; Drive outcome is recorded separately in GitHub."


def nonnegative_int(value) -> int | None:
    return value if type(value) is int and value >= 0 else None


def read_runs(session: Session, limit: int) -> WorkerHistory:
    runs = session.scalars(select(IngestionRun).where(
        IngestionRun.statistics["stage"].as_string() == "daily_worker"
    ).order_by(IngestionRun.created_at.desc(), IngestionRun.id.desc()).limit(limit))
    items = []
    for run in runs:
        stats = run.statistics
        scan = stats.get("archive_scan")
        scan = scan if isinstance(scan, dict) else {}
        failures = scan.get("page_failures")
        items.append(WorkerRun(
            id=run.id, status=run.status, trigger=run.trigger,
            started_at=run.created_at, finished_at=run.finished_at,
            counters={key: nonnegative_int(stats.get(key)) for key in COUNTERS},
            pages_scanned=nonnegative_int(scan.get("pages_scanned")),
            archive_page_failures=len(failures) if isinstance(failures, list) else None,
        ))
    return WorkerHistory(items=items, limit=limit)


class MasterSource(BaseModel):
    id: str
    url: str
    sha256: str
    category: str


class MasterMeasurement(BaseModel):
    metric: str
    value: str | None
    unit: str
    zone: str
    period: str
    fuel: str | None
    source_id: str
    source_page: int | None
    raw_text: str | None


class MasterDay(BaseModel):
    operational_date: date
    report_version_id: str
    parser_version: str
    available_at: datetime | None
    sources: list[MasterSource]
    measurements: list[MasterMeasurement]


class MasterPage(BaseModel):
    scope: str = "Current validated national daily records"
    total_dates: int
    page: int
    page_size: int
    total_pages: int
    items: list[MasterDay]


def read_master(
    session: Session, start_date: date | None = None, end_date: date | None = None,
    page: int = 1, page_size: int = 20,
) -> MasterPage:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "start_date must not be after end_date")
    if not 1 <= page <= 100000 or not 1 <= page_size <= 100:
        raise HTTPException(422, "Invalid pagination")
    query = canonical_query()
    if start_date:
        query = query.where(DailyReport.report_date >= start_date)
    if end_date:
        query = query.where(DailyReport.report_date <= end_date)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.order_by(DailyReport.report_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size)).all()
    days = {
        row.version_id: MasterDay(
            operational_date=row.operational_date, report_version_id=row.version_id,
            parser_version=row.parser_version, available_at=row.available_at,
            sources=[], measurements=[],
        ) for row in rows
    }
    if days:
        links = session.execute(select(VersionSource.version_id, SourceDocument).join(
            SourceDocument, VersionSource.source_id == SourceDocument.id
        ).where(VersionSource.version_id.in_(days)).order_by(
            SourceDocument.original_url, SourceDocument.id
        ))
        linked = {version: set() for version in days}
        for version, source in links:
            linked[version].add(source.id)
            days[version].sources.append(MasterSource(
                id=source.id, url=source.original_url, sha256=source.sha256,
                category=source.category,
            ))
        seen = set()
        for table in TABLES:
            measurements = session.scalars(select(table).where(
                table.version_id.in_(days), table.zone == "national"
            ))
            for item in measurements:
                fuel = getattr(item, "fuel", None)
                grain = (item.version_id, item.metric, item.zone, item.period, item.unit, fuel)
                if (grain in seen or item.source_id not in linked[item.version_id]
                        or (item.value is not None and not item.value.is_finite())):
                    raise HTTPException(503, "Canonical data consistency check failed")
                seen.add(grain)
                days[item.version_id].measurements.append(MasterMeasurement(
                    metric=item.metric, value=str(item.value) if item.value is not None else None,
                    unit=item.unit, zone=item.zone, period=item.period, fuel=fuel,
                    source_id=item.source_id, source_page=item.source_page, raw_text=item.raw_text,
                ))
        for day in days.values():
            if not day.sources or not day.measurements:
                raise HTTPException(503, "Canonical data consistency check failed")
            day.measurements.sort(key=lambda m: (m.metric, m.period, m.unit, m.fuel or ""))
    return MasterPage(
        total_dates=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size, items=list(days.values()),
    )


@router.get("/dataset/summary", response_model=DatasetSummary)
def summary(response: Response, session: Database) -> DatasetSummary:
    response.headers["Cache-Control"] = "no-store"
    return read_summary(session)


@router.get("/collection/runs", response_model=WorkerHistory)
def runs(
    response: Response, session: Database, limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> WorkerHistory:
    response.headers["Cache-Control"] = "no-store"
    return read_runs(session, limit)


@router.get("/dataset/daily", response_model=MasterPage)
def daily(
    response: Response, session: Database, start_date: date | None = None,
    end_date: date | None = None, page: Annotated[int, Query(ge=1, le=100000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MasterPage:
    response.headers["Cache-Control"] = "no-store"
    return read_master(session, start_date, end_date, page, page_size)
