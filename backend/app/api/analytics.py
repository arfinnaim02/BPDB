"""Observed national descriptive analytics. No imputation, forecasts or causal claims."""

import calendar
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from statistics import median
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.api.monitoring import Database, canonical_query
from app.db.models import DemandObservation, GenerationObservation, VersionSource

router = APIRouter(prefix="/api/v1/analytics", tags=["Historical analytics"])
MetricName = Literal[
    "day_peak_generation",
    "evening_peak_generation",
    "day_peak_demand",
    "evening_peak_demand",
    "minimum_generation",
    "maximum_generation",
    "energy_generated",
    "energy_demand",
    "energy_unserved",
]
Resolution = Literal["daily", "monthly", "yearly"]
# Label, expected table, unit, period, supported by both existing parser families.
METRICS = {
    "day_peak_generation": ("Day peak generation", GenerationObservation, "MW", "day_peak", True),
    "evening_peak_generation": (
        "Evening peak generation",
        GenerationObservation,
        "MW",
        "evening_peak",
        True,
    ),
    "day_peak_demand": ("Day peak demand", DemandObservation, "MW", "day_peak", False),
    "evening_peak_demand": ("Evening peak demand", DemandObservation, "MW", "evening_peak", True),
    "minimum_generation": (
        "Minimum generation",
        GenerationObservation,
        "MW",
        "daily_minimum",
        False,
    ),
    "maximum_generation": (
        "Maximum generation",
        GenerationObservation,
        "MW",
        "daily_maximum",
        True,
    ),
    "energy_generated": (
        "Energy generated",
        GenerationObservation,
        "million_kWh",
        "daily",
        True,
    ),
    "energy_demand": ("Energy demand", DemandObservation, "million_kWh", "daily", False),
    "energy_unserved": ("Energy unserved", DemandObservation, "million_kWh", "daily", False),
}
MAX_POINTS = 10000


def number(value: Decimal | None) -> str | None:
    if value is None:
        return None
    value = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)
    if value == 0:
        return "0"
    return format(value, "f").rstrip("0").rstrip(".")


def percent(n: int, total: int) -> float | None:
    return round(100 * n / total, 2) if total else None


class Statistics(BaseModel):
    observations: int
    zero_days: int
    mean: str | None
    median: str | None
    minimum: str | None
    maximum: str | None
    sample_stddev: str | None
    observed_total: str | None


def statistics(values: list[Decimal], energy: bool) -> Statistics:
    with localcontext() as context:
        context.prec = 50
        size = len(values)
        average = sum(values, Decimal(0)) / size if size else None
        variance = (
            sum(((x - average) ** 2 for x in values), Decimal(0)) / (size - 1) if size > 1 else None
        )
        return Statistics(
            observations=size,
            zero_days=sum(x == 0 for x in values),
            mean=number(average),
            median=number(median(values)) if size else None,
            minimum=number(min(values)) if size else None,
            maximum=number(max(values)) if size else None,
            sample_stddev=number(variance.sqrt()) if variance is not None else None,
            observed_total=number(sum(values, Decimal(0))) if size and energy else None,
        )


class PeriodPoint(BaseModel):
    label: str
    start_date: date
    end_date: date
    value: str | None
    mean: str | None
    minimum: str | None
    maximum: str | None
    observed_days: int
    canonical_dates: int
    expected_days: int
    coverage_percent: float | None
    zero_days: int
    full_period_selected: bool
    complete_period: bool


class AnalyticsReport(BaseModel):
    scope: str = "Observed current validated national records; descriptive analysis only"
    generated_at: datetime
    metric: str
    label: str
    unit: str
    period: str
    resolution: Resolution
    aggregation: str
    parser_support: str
    earliest_canonical_date: date | None
    latest_canonical_date: date | None
    start_date: date | None
    end_date: date | None
    calendar_days: int
    canonical_dates: int
    missing_canonical_dates: int
    unavailable_metric_dates: int
    metric_calendar_coverage_percent: float | None
    metric_canonical_coverage_percent: float | None
    first_value_date: date | None
    last_value_date: date | None
    statistics: Statistics
    points: list[PeriodPoint]
    data_fingerprint: str
    limitation: str = (
        "No values are imputed. MW period values are means of observed daily measurements; "
        "energy period values are observed sums, not estimated complete-period totals. "
        "Derived statistics are rounded to six decimals, half-even. "
        "Missing dates and layout-dependent fields remain unavailable. "
        "Availability and descriptive patterns do not prove accuracy or causality."
    )


def period_start(day: date, resolution: Resolution) -> date:
    if resolution == "monthly":
        return day.replace(day=1)
    if resolution == "yearly":
        return date(day.year, 1, 1)
    return day


def period_end(day: date, resolution: Resolution) -> date:
    if resolution == "monthly":
        return day.replace(day=calendar.monthrange(day.year, day.month)[1])
    if resolution == "yearly":
        return date(day.year, 12, 31)
    return day


def read_analytics(
    session: Session,
    metric: str = "day_peak_generation",
    resolution: Resolution = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
) -> AnalyticsReport:
    if metric not in METRICS or resolution not in ("daily", "monthly", "yearly"):
        raise HTTPException(422, "Unsupported metric or resolution")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "start_date must not be after end_date")
    label, table, unit, expected_period, shared = METRICS[metric]
    energy = unit == "million_kWh"
    eligible = canonical_query().cte("analytics_canonical")
    canonical = session.execute(
        select(eligible.c.operational_date, eligible.c.version_id).order_by(
            eligible.c.operational_date
        )
    ).all()
    first = canonical[0].operational_date if canonical else None
    last = canonical[-1].operational_date if canonical else None
    start = max(start_date or first, first) if first else None
    end = min(end_date or last, last) if last else None
    if start and end and start > end:
        start = end = None
    selected = [r for r in canonical if start and start <= r.operational_date <= end]
    by_date = {}
    raw_values = []
    if selected:
        source_link = exists(
            select(VersionSource.version_id).where(
                VersionSource.version_id == table.version_id,
                VersionSource.source_id == table.source_id,
            )
        )
        measurements = session.execute(
            select(
                eligible.c.operational_date,
                table.version_id,
                table.source_id,
                table.value,
                table.unit,
                table.period,
                source_link.label("source_linked"),
            )
            .join(eligible, table.version_id == eligible.c.version_id)
            .where(
                eligible.c.operational_date.between(start, end),
                table.metric == metric,
                table.zone == "national",
            )
            .order_by(eligible.c.operational_date, table.id)
        ).all()
        for row in measurements:
            if (
                row.operational_date in by_date
                or row.unit != unit
                or row.period != expected_period
                or not row.source_linked
                or (row.value is not None and not row.value.is_finite())
            ):
                raise HTTPException(503, "Analytics measurements require a consistency review")
            by_date[row.operational_date] = row.value
            raw_values.append(
                (
                    row.operational_date.isoformat(),
                    row.version_id,
                    row.source_id,
                    str(row.value) if row.value is not None else None,
                )
            )
    span = (end - start).days + 1 if start else 0
    if resolution == "daily" and span > MAX_POINTS:
        raise HTTPException(422, "Use monthly/yearly resolution or a narrower date range")
    values_by_period = defaultdict(list)
    for day, value in by_date.items():
        if value is not None:
            values_by_period[period_start(day, resolution)].append(value)
    canonical_by_period = Counter(period_start(r.operational_date, resolution) for r in selected)
    observed = [(day, value) for day, value in by_date.items() if value is not None]
    stats = statistics([value for _, value in observed], energy)
    points = []
    cursor = period_start(start, resolution) if start else None
    while cursor and cursor <= end:
        if len(points) == MAX_POINTS:
            raise HTTPException(422, "Use a narrower date range")
        finish = period_end(cursor, resolution)
        window_start, window_end = max(cursor, start), min(finish, end)
        expected = (window_end - window_start).days + 1
        bucket = statistics(values_by_period[cursor], energy)
        value = bucket.observed_total if energy else bucket.mean
        full = window_start == cursor and window_end == finish
        points.append(
            PeriodPoint(
                label=cursor.isoformat()
                if resolution == "daily"
                else (cursor.strftime("%Y-%m") if resolution == "monthly" else str(cursor.year)),
                start_date=window_start,
                end_date=window_end,
                value=value,
                mean=bucket.mean,
                minimum=bucket.minimum,
                maximum=bucket.maximum,
                observed_days=bucket.observations,
                canonical_dates=canonical_by_period[cursor],
                expected_days=expected,
                zero_days=bucket.zero_days,
                coverage_percent=percent(bucket.observations, expected),
                full_period_selected=full,
                complete_period=full and bucket.observations == expected,
            )
        )
        if finish >= end:
            break
        cursor = finish + timedelta(days=1)
    payload = {
        "metric": metric,
        "unit": unit,
        "period": expected_period,
        "start": str(start),
        "end": str(end),
        "versions": [(r.operational_date.isoformat(), r.version_id) for r in selected],
        "observations": raw_values,
    }
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return AnalyticsReport(
        generated_at=datetime.now(timezone.utc),
        metric=metric,
        label=label,
        unit=unit,
        period=expected_period,
        resolution=resolution,
        aggregation="observed_sum" if energy else "observed_mean",
        parser_support="legacy_and_modern" if shared else "modern_parser_only",
        earliest_canonical_date=first,
        latest_canonical_date=last,
        start_date=start,
        end_date=end,
        calendar_days=span,
        canonical_dates=len(selected),
        missing_canonical_dates=span - len(selected),
        unavailable_metric_dates=len(selected) - len(observed),
        metric_calendar_coverage_percent=percent(len(observed), span),
        metric_canonical_coverage_percent=percent(len(observed), len(selected)),
        first_value_date=min((day for day, _ in observed), default=None),
        last_value_date=max((day for day, _ in observed), default=None),
        statistics=stats,
        points=points,
        data_fingerprint=fingerprint,
    )


@router.get("/generation-demand", response_model=AnalyticsReport)
def generation_demand(
    response: Response,
    session: Database,
    metric: MetricName = "day_peak_generation",
    resolution: Resolution = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
) -> AnalyticsReport:
    response.headers["Cache-Control"] = "no-store"
    return read_analytics(session, metric, resolution, start_date, end_date)
