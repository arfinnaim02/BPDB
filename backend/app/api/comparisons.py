"""Coverage-aware historical comparisons. No forecasts, imputation or causal inference."""

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.analytics import (
    MetricName,
    PeriodPoint,
    Resolution,
    number,
    percent,
    period_end,
    period_start,
    read_analytics,
    statistics,
)
from app.api.measurement_review import read_review
from app.api.monitoring import Database

router = APIRouter(prefix="/api/v1/analytics", tags=["Historical comparisons"])
Peak = Literal["evening", "day"]


class MonthlyComparison(PeriodPoint):
    mom_percent: str | None
    mom_status: str
    yoy_percent: str | None
    yoy_status: str


class PairedPoint(BaseModel):
    label: str
    start_date: date
    end_date: date
    paired_days: int
    expected_days: int
    coverage_percent: float | None
    complete_period: bool
    generation_mean: str | None
    demand_mean: str | None
    difference_mean: str | None


class ComparisonReport(BaseModel):
    generated_at: datetime
    scope: str = "Current validated national observations; descriptive comparisons only"
    metric: str
    label: str
    unit: str
    aggregation: str
    parser_support: str
    start_date: date | None
    end_date: date | None
    canonical_dates: int
    calendar_days: int
    metric_observed_days: int
    available_years: list[int]
    selected_years: list[int]
    monthly: list[MonthlyComparison]
    annual: list[PeriodPoint]
    peak: Peak
    resolution: Resolution
    paired_days: int
    paired_coverage_percent: float | None
    paired_difference_mean: str | None
    demand_above_generation_days: int
    generation_above_demand_days: int
    equal_days: int
    paired_points: list[PairedPoint]
    generation_energy_review_dates: int
    review_rule_version: str
    data_fingerprint: str
    limitation: str = (
        "Comparisons include current canonical values, including unresolved review candidates. "
        "Monthly/annual energy values are observed sums; MW values are observed daily means. "
        "Percentage changes are withheld unless both compared calendar months are fully observed "
        "and selected, and the baseline is nonzero. Seasonal patterns are descriptive. "
        "Demand minus generation is a signed comparison, not recorded load shedding. "
        "No missing value is imputed and no measurement is corrected or excluded here."
    )


def buckets(start: date | None, end: date | None, resolution: Resolution):
    cursor = period_start(start, resolution) if start else None
    while cursor and cursor <= end:
        finish = period_end(cursor, resolution)
        left, right = max(start, cursor), min(end, finish)
        label = (
            cursor.isoformat()
            if resolution == "daily"
            else cursor.strftime("%Y-%m")
            if resolution == "monthly"
            else str(cursor.year)
        )
        yield (
            cursor,
            label,
            left,
            right,
            (right - left).days + 1,
            left == cursor and right == finish,
        )
        if finish >= end:
            break
        cursor = finish + timedelta(days=1)


def aggregate(
    daily: list[PeriodPoint],
    start: date | None,
    end: date | None,
    resolution: Resolution,
    energy: bool,
) -> list[PeriodPoint]:
    values = defaultdict(list)
    canonical = defaultdict(int)
    for point in daily:
        key = period_start(point.start_date, resolution)
        canonical[key] += point.canonical_dates
        if point.value is not None:
            values[key].append(Decimal(point.value))
    result = []
    for cursor, label, left, right, expected, full in buckets(start, end, resolution):
        stats = statistics(values[cursor], energy)
        result.append(
            PeriodPoint(
                label=label,
                start_date=left,
                end_date=right,
                value=stats.observed_total if energy else stats.mean,
                mean=stats.mean,
                minimum=stats.minimum,
                maximum=stats.maximum,
                observed_days=stats.observations,
                canonical_dates=canonical[cursor],
                expected_days=expected,
                zero_days=stats.zero_days,
                coverage_percent=percent(stats.observations, expected),
                full_period_selected=full,
                complete_period=full and stats.observations == expected,
            )
        )
    return result


def change(current: PeriodPoint, previous: PeriodPoint | None) -> tuple[str | None, str]:
    if not current.complete_period:
        return None, "current_month_incomplete"
    if previous is None:
        return None, "baseline_outside_window"
    if not previous.complete_period:
        return None, "baseline_month_incomplete"
    if previous.value is None or current.value is None:
        return None, "unavailable"
    if Decimal(previous.value) == 0:
        return None, "zero_baseline"
    with localcontext() as context:
        context.prec = 50
        value = (
            (Decimal(current.value) - Decimal(previous.value)) / abs(Decimal(previous.value)) * 100
        )
        return number(value), "comparable_complete_months"


def monthly_changes(points: list[PeriodPoint]) -> list[MonthlyComparison]:
    lookup = {p.label: p for p in points}
    result = []
    for point in points:
        first = date.fromisoformat(point.label + "-01")
        previous_month = (first - timedelta(days=1)).strftime("%Y-%m")
        previous_year = f"{first.year - 1:04d}-{first.month:02d}"
        mom, mom_status = change(point, lookup.get(previous_month))
        yoy, yoy_status = change(point, lookup.get(previous_year))
        result.append(
            MonthlyComparison(
                **point.model_dump(),
                mom_percent=mom,
                mom_status=mom_status,
                yoy_percent=yoy,
                yoy_status=yoy_status,
            )
        )
    return result


def read_comparisons(
    session: Session,
    metric: str = "day_peak_generation",
    peak: Peak = "evening",
    resolution: Resolution = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
    years: list[int] | None = None,
) -> ComparisonReport:
    if peak not in ("evening", "day") or resolution not in ("daily", "monthly", "yearly"):
        raise HTTPException(422, "Unsupported peak or resolution")
    if years is not None and (len(years) > 8 or any(y < 1900 or y > 2200 for y in years)):
        raise HTTPException(422, "Select at most eight years between 1900 and 2200")
    names = [metric, f"{peak}_peak_generation", f"{peak}_peak_demand"]
    # Read all inputs from the same request's repeatable-read snapshot. Reuse identical metrics.
    series = {
        name: read_analytics(session, name, "daily", start_date, end_date)
        for name in dict.fromkeys(names)
    }
    selected, generation, demand = (series[name] for name in names)
    start, end = selected.start_date, selected.end_date
    available = list(range(start.year, end.year + 1)) if start else []
    chosen = sorted(set(years)) if years else available[-3:]
    chosen = [year for year in chosen if year in available]
    energy = selected.unit == "million_kWh"
    monthly = aggregate(selected.points, start, end, "monthly", energy)
    annual = aggregate(selected.points, start, end, "yearly", energy)
    gen_map = {p.start_date: Decimal(p.value) for p in generation.points if p.value is not None}
    demand_map = {p.start_date: Decimal(p.value) for p in demand.points if p.value is not None}
    dates = sorted(gen_map.keys() & demand_map.keys())
    pairs = [(day, gen_map[day], demand_map[day]) for day in dates]
    grouped = defaultdict(list)
    for day, gen, dem in pairs:
        grouped[period_start(day, resolution)].append((gen, dem))
    paired_points = []
    for cursor, label, left, right, expected, full in buckets(start, end, resolution):
        pairs_in_period = grouped[cursor]
        gen_stats = statistics([g for g, _ in pairs_in_period], False)
        dem_stats = statistics([d for _, d in pairs_in_period], False)
        differences = statistics([d - g for g, d in pairs_in_period], False)
        paired_points.append(
            PairedPoint(
                label=label,
                start_date=left,
                end_date=right,
                paired_days=len(pairs_in_period),
                expected_days=expected,
                coverage_percent=percent(len(pairs_in_period), expected),
                complete_period=full and len(pairs_in_period) == expected,
                generation_mean=gen_stats.mean,
                demand_mean=dem_stats.mean,
                difference_mean=differences.mean,
            )
        )
    differences = [dem - gen for _, gen, dem in pairs]
    review = read_review(session, page_size=1, start_date=start_date, end_date=end_date)
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "rules": "historical_comparisons_v1",
                "inputs": {n: s.data_fingerprint for n, s in series.items()},
                "review": review.data_fingerprint,
                "years": chosen,
                "peak": peak,
                "resolution": resolution,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return ComparisonReport(
        generated_at=datetime.now(timezone.utc),
        metric=selected.metric,
        label=selected.label,
        unit=selected.unit,
        aggregation=selected.aggregation,
        parser_support=selected.parser_support,
        start_date=start,
        end_date=end,
        canonical_dates=selected.canonical_dates,
        calendar_days=selected.calendar_days,
        metric_observed_days=selected.statistics.observations,
        available_years=available,
        selected_years=chosen,
        monthly=[p for p in monthly_changes(monthly) if p.start_date.year in chosen],
        annual=[p for p in annual if p.start_date.year in chosen],
        peak=peak,
        resolution=resolution,
        paired_days=len(pairs),
        paired_coverage_percent=percent(len(pairs), selected.calendar_days),
        paired_difference_mean=statistics(differences, False).mean,
        demand_above_generation_days=sum(d > 0 for d in differences),
        generation_above_demand_days=sum(d < 0 for d in differences),
        equal_days=sum(d == 0 for d in differences),
        paired_points=paired_points,
        generation_energy_review_dates=review.flagged_dates,
        review_rule_version=review.rule_version,
        data_fingerprint=fingerprint,
    )


@router.get("/comparisons", response_model=ComparisonReport)
def comparisons(
    response: Response,
    session: Database,
    metric: MetricName = "day_peak_generation",
    peak: Peak = "evening",
    resolution: Resolution = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
    year: Annotated[list[int] | None, Query(max_length=8)] = None,
) -> ComparisonReport:
    response.headers["Cache-Control"] = "no-store"
    return read_comparisons(session, metric, peak, resolution, start_date, end_date, year)
