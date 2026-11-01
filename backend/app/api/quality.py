"""Whole-history availability, not a substitute for measurement/source validation."""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import String, case, distinct, extract, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.api.monitoring import DAILY_COLUMNS, TABLES, Database, canonical_query

router = APIRouter(prefix="/api/v1/dataset", tags=["Data quality"])


def percentage(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 2) if denominator else None


class CalendarYear(BaseModel):
    year: int
    calendar_days: int
    canonical_dates: int
    missing_dates: int
    coverage_percent: float | None


class MetricYear(BaseModel):
    year: int
    canonical_dates: int
    non_null_dates: int
    missing_or_null_dates: int
    zero_dates: int
    coverage_percent: float | None


class MetricCoverage(BaseModel):
    metric: str
    label: str
    unit: str
    period: str
    fuel: str | None
    canonical_dates: int
    non_null_dates: int
    missing_or_null_dates: int
    zero_dates: int
    earliest_value_date: date | None
    latest_value_date: date | None
    coverage_percent: float | None
    by_year: list[MetricYear]


class GapRange(BaseModel):
    start_date: date
    end_date: date
    days: int
    status: str = "missing_canonical_record"
    source_report_status: str = "not_assessed"


class GapPage(BaseModel):
    missing_dates: int
    total_ranges: int
    page: int
    page_size: int
    total_pages: int
    items: list[GapRange]


class QualityReport(BaseModel):
    scope: str = "All current validated national daily records"
    generated_at: datetime
    canonical_dates: int
    earliest_operational_date: date | None
    latest_operational_date: date | None
    calendar_days: int
    missing_dates: int
    calendar_coverage_percent: float | None
    years: list[CalendarYear]
    metrics: list[MetricCoverage]
    gaps: GapPage
    limitation: str = (
        "Availability is not measurement validation. Metric coverage uses canonical dates; "
        "calendar coverage uses all days between observed bounds. A calendar gap does not "
        "prove a missing official report. No source-cause investigation is performed here."
    )


def read_quality(session: Session, gap_page: int = 1, gap_page_size: int = 20) -> QualityReport:
    if not 1 <= gap_page <= 100000 or not 1 <= gap_page_size <= 100:
        raise HTTPException(422, "Invalid gap pagination")
    eligible = canonical_query().cte("quality_canonical")
    dates = list(session.scalars(select(eligible.c.operational_date).order_by(
        eligible.c.operational_date
    )))
    first = dates[0] if dates else None
    last = dates[-1] if dates else None
    span = (last - first).days + 1 if dates else 0
    counts = Counter(day.year for day in dates)
    years = []
    if dates:
        for year in range(first.year, last.year + 1):
            start = max(first, date(year, 1, 1))
            end = min(last, date(year, 12, 31))
            calendar_days = (end - start).days + 1
            years.append(CalendarYear(
                year=year, calendar_days=calendar_days, canonical_dates=counts[year],
                missing_dates=calendar_days - counts[year],
                coverage_percent=percentage(counts[year], calendar_days),
            ))
    gaps = []
    for previous, following in zip(dates, dates[1:]):
        length = (following - previous).days - 1
        if length:
            gaps.append(GapRange(
                start_date=previous + timedelta(days=1),
                end_date=following - timedelta(days=1), days=length,
            ))

    # At most two read statements per request, independent of dates/pages in the archive.
    # Group on the entire metric grain so different units/periods/fuels cannot be conflated.
    groups = []
    if dates:
        parts = []
        for table in TABLES:
            parts.append(select(
                eligible.c.operational_date.label("day"), table.metric.label("metric"),
                table.unit.label("unit"), table.period.label("period"),
                getattr(table, "fuel", literal(None, type_=String)).label("fuel"),
                table.value.label("value"),
            ).join(eligible, table.version_id == eligible.c.version_id).where(
                table.zone == "national"
            ))
        observations = union_all(*parts).subquery("quality_observations")
        year_column = extract("year", observations.c.day).label("year")
        non_null_day = case((observations.c.value.is_not(None), observations.c.day))
        zero_day = case((observations.c.value == 0, observations.c.day))
        groups = session.execute(select(
            observations.c.metric, observations.c.unit, observations.c.period,
            observations.c.fuel, year_column,
            func.count(distinct(non_null_day)).label("non_null_dates"),
            func.count(distinct(zero_day)).label("zero_dates"),
            func.min(non_null_day).label("first_value"),
            func.max(non_null_day).label("last_value"),
        ).group_by(
            observations.c.metric, observations.c.unit, observations.c.period,
            observations.c.fuel, year_column,
        )).all()

    labels = {column[1:]: column[0] for column in DAILY_COLUMNS}
    grouped = {key: {} for key in labels}
    for row in groups:
        key = (row.metric, row.unit, row.period, row.fuel)
        grouped.setdefault(key, {})[int(row.year)] = row
    metrics = []
    extra = sorted((key for key in grouped if key not in labels), key=lambda k: tuple(
        item or "" for item in k
    ))
    for key in [*labels, *extra]:
        metric, unit, period, fuel = key
        rows = grouped[key]
        non_null = sum(row.non_null_dates for row in rows.values())
        zero = sum(row.zero_dates for row in rows.values())
        first_values = [row.first_value for row in rows.values() if row.first_value is not None]
        last_values = [row.last_value for row in rows.values() if row.last_value is not None]
        metrics.append(MetricCoverage(
            metric=metric, label=labels.get(key, metric.replace("_", " ").capitalize()),
            unit=unit, period=period, fuel=fuel,
            canonical_dates=len(dates), non_null_dates=non_null,
            missing_or_null_dates=len(dates) - non_null, zero_dates=zero,
            earliest_value_date=min(first_values) if first_values else None,
            latest_value_date=max(last_values) if last_values else None,
            coverage_percent=percentage(non_null, len(dates)),
            by_year=[MetricYear(
                year=y.year, canonical_dates=y.canonical_dates,
                non_null_dates=rows[y.year].non_null_dates if y.year in rows else 0,
                zero_dates=rows[y.year].zero_dates if y.year in rows else 0,
                missing_or_null_dates=y.canonical_dates - (
                    rows[y.year].non_null_dates if y.year in rows else 0
                ),
                coverage_percent=percentage(
                    rows[y.year].non_null_dates if y.year in rows else 0, y.canonical_dates,
                ),
            ) for y in years],
        ))
    offset = (gap_page - 1) * gap_page_size
    return QualityReport(
        generated_at=datetime.now(timezone.utc), canonical_dates=len(dates),
        earliest_operational_date=first, latest_operational_date=last,
        calendar_days=span, missing_dates=span - len(dates),
        calendar_coverage_percent=percentage(len(dates), span), years=years, metrics=metrics,
        gaps=GapPage(
            missing_dates=span - len(dates), total_ranges=len(gaps), page=gap_page,
            page_size=gap_page_size, total_pages=(len(gaps) + gap_page_size - 1) // gap_page_size,
            items=gaps[offset:offset + gap_page_size],
        ),
    )


@router.get("/quality", response_model=QualityReport)
def quality(
    response: Response, session: Database,
    gap_page: Annotated[int, Query(ge=1, le=100000)] = 1,
    gap_page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> QualityReport:
    response.headers["Cache-Control"] = "no-store"
    return read_quality(session, gap_page, gap_page_size)
