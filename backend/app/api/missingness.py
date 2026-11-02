"""Read-only missing-data assessment. Observed availability does not establish a cause."""

import hashlib
import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import String, exists, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.api.analytics import percent, period_end
from app.api.monitoring import DAILY_COLUMNS, TABLES, Database, canonical_query
from app.db.models import (
    CostObservation,
    DemandObservation,
    EnvironmentObservation,
    FuelObservation,
    GenerationObservation,
    VersionSource,
)

router = APIRouter(prefix="/api/v1/dataset", tags=["Missing data"])
MissingMetric = Literal[
    "day_peak_generation",
    "evening_peak_generation",
    "day_peak_demand",
    "evening_peak_demand",
    "minimum_generation",
    "maximum_generation",
    "energy_generated",
    "energy_demand",
    "energy_unserved",
    "maximum_temperature",
    "gas_supplied",
    "production_cost_per_kwh",
    "total_production_cost",
]
SHARED = {
    "day_peak_generation",
    "evening_peak_generation",
    "evening_peak_demand",
    "maximum_generation",
    "energy_generated",
}
TABLE_FOR = {
    **{
        name: GenerationObservation
        for name in (
            "day_peak_generation",
            "evening_peak_generation",
            "minimum_generation",
            "maximum_generation",
            "energy_generated",
        )
    },
    **{
        name: DemandObservation
        for name in (
            "day_peak_demand",
            "evening_peak_demand",
            "energy_demand",
            "energy_unserved",
        )
    },
    "maximum_temperature": EnvironmentObservation,
    "gas_supplied": FuelObservation,
    "production_cost_per_kwh": CostObservation,
    "total_production_cost": CostObservation,
}
RULE_VERSION = "missingness_v1"
MONTH_PAGE_SIZE = 24


class MissingRun(BaseModel):
    start_date: date
    end_date: date
    days: int
    missing_canonical_days: int
    absent_field_days: int
    explicit_null_days: int
    position: str
    source_cause: str = "not_assessed"


class MissingMonth(BaseModel):
    label: str
    start_date: date
    end_date: date
    calendar_days: int
    canonical_dates: int
    observed_days: int
    zero_days: int
    missing_canonical_days: int
    absent_field_days: int
    explicit_null_days: int
    whole_calendar_month_selected: bool
    all_calendar_days_observed: bool
    status: str


class MissingSummary(BaseModel):
    metric: str
    label: str
    unit: str
    period: str
    fuel: str | None
    parser_support: str
    observed_days: int
    zero_days: int
    unavailable_days: int
    calendar_coverage_percent: float | None
    missing_canonical_days: int
    absent_field_days: int
    explicit_null_days: int
    first_value_date: date | None
    last_value_date: date | None
    before_first_value_days: int | None
    after_last_value_days: int | None
    internal_missing_days: int | None
    missing_runs: int
    longest_missing_run: int
    longest_internal_missing_run: int | None
    longest_observed_streak: int
    latest_observed_streak: int
    months_in_window: int
    whole_months_selected: int
    complete_months: int
    incomplete_whole_months: int
    sliced_months: int
    zero_observation_months: int
    longest_complete_month_streak: int


class RunBin(BaseModel):
    label: str
    runs: int
    days: int


class MissingReport(BaseModel):
    generated_at: datetime
    rule_version: str = RULE_VERSION
    scope: str = "Current validated national records; availability-only assessment"
    earliest_canonical_date: date | None
    latest_canonical_date: date | None
    start_date: date | None
    end_date: date | None
    calendar_days: int
    canonical_dates: int
    missing_canonical_days: int
    metrics: list[MissingSummary]
    selected: MissingSummary
    run_bins: list[RunBin]
    gap_page: int
    gap_page_size: int
    gap_total_pages: int
    gaps: list[MissingRun]
    month_page: int
    month_page_size: int = MONTH_PAGE_SIZE
    month_total_pages: int
    months: list[MissingMonth]
    next_steps: list[str]
    data_fingerprint: str
    limitation: str = (
        "No values are filled, corrected, removed or marked model-ready. Missing canonical "
        "records do not prove absent official reports. Absent/null fields do not prove parser "
        "failure. Leading/trailing unavailability and parser capability do not establish "
        "structural absence in a PDF. Complete months certify availability only, not accuracy, "
        "definition comparability or forecasting suitability. Runs are bounded by this window."
    )


def analyse_metric(
    column, canonical: set[date], values: dict, start: date | None, end: date | None
):
    label, metric, unit, period, fuel = column
    span = (end - start).days + 1 if start else 0
    observed = sorted(day for day, value in values.items() if value is not None)
    first = observed[0] if observed else None
    last = observed[-1] if observed else None
    classes = {}
    zeroes = 0
    streak = longest_streak = 0
    for offset in range(span):
        day = start + timedelta(days=offset)
        if day not in canonical:
            category = "missing_canonical_days"
        elif day not in values:
            category = "absent_field_days"
        elif values[day] is None:
            category = "explicit_null_days"
        else:
            category = "observed"
            zeroes += int(values[day] == 0)
        classes[day] = category
        streak = streak + 1 if category == "observed" else 0
        longest_streak = max(longest_streak, streak)
    totals = Counter(classes.values())
    runs = []
    pending = []

    def close_run():
        if not pending:
            return
        counts = Counter(classes[day] for day in pending)
        position = (
            "no_observed_window"
            if first is None
            else "leading"
            if pending[-1] < first
            else "trailing"
            if pending[0] > last
            else "internal"
        )
        runs.append(
            MissingRun(
                start_date=pending[0],
                end_date=pending[-1],
                days=len(pending),
                position=position,
                missing_canonical_days=counts["missing_canonical_days"],
                absent_field_days=counts["absent_field_days"],
                explicit_null_days=counts["explicit_null_days"],
            )
        )
        pending.clear()

    for day, category in classes.items():
        if category == "observed":
            close_run()
        else:
            pending.append(day)
    close_run()
    months = []
    cursor = start.replace(day=1) if start else None
    complete_streak = longest_complete = 0
    while cursor and cursor <= end:
        finish = period_end(cursor, "monthly")
        left, right = max(start, cursor), min(end, finish)
        days = (right - left).days + 1
        counts = Counter(classes[left + timedelta(days=i)] for i in range(days))
        whole = left == cursor and right == finish
        complete = whole and counts["observed"] == days
        complete_streak = complete_streak + 1 if complete else 0
        longest_complete = max(longest_complete, complete_streak)
        status = (
            "all_days_observed"
            if complete
            else "no_observations"
            if not counts["observed"]
            else "window_slice"
            if not whole
            else "incomplete_month"
        )
        months.append(
            MissingMonth(
                label=cursor.strftime("%Y-%m"),
                start_date=left,
                end_date=right,
                calendar_days=days,
                canonical_dates=days - counts["missing_canonical_days"],
                observed_days=counts["observed"],
                zero_days=sum(
                    day in values and values[day] == 0
                    for day in (left + timedelta(days=i) for i in range(days))
                ),
                missing_canonical_days=counts["missing_canonical_days"],
                absent_field_days=counts["absent_field_days"],
                explicit_null_days=counts["explicit_null_days"],
                whole_calendar_month_selected=whole,
                all_calendar_days_observed=complete,
                status=status,
            )
        )
        if finish >= end:
            break
        cursor = finish + timedelta(days=1)
    internal = [run for run in runs if run.position == "internal"]
    whole_count = sum(m.whole_calendar_month_selected for m in months)
    complete_count = sum(m.all_calendar_days_observed for m in months)
    summary = MissingSummary(
        metric=metric,
        label=label,
        unit=unit,
        period=period,
        fuel=fuel,
        parser_support="legacy_and_modern" if metric in SHARED else "modern_parser_only",
        observed_days=len(observed),
        zero_days=zeroes,
        unavailable_days=span - len(observed),
        calendar_coverage_percent=percent(len(observed), span),
        missing_canonical_days=totals["missing_canonical_days"],
        absent_field_days=totals["absent_field_days"],
        explicit_null_days=totals["explicit_null_days"],
        first_value_date=first,
        last_value_date=last,
        before_first_value_days=(first - start).days if first else None,
        after_last_value_days=(end - last).days if last else None,
        internal_missing_days=sum(run.days for run in internal) if observed else None,
        missing_runs=len(runs),
        longest_missing_run=max((r.days for r in runs), default=0),
        longest_internal_missing_run=max((r.days for r in internal), default=0)
        if observed
        else None,
        longest_observed_streak=longest_streak,
        latest_observed_streak=streak,
        months_in_window=len(months),
        whole_months_selected=whole_count,
        complete_months=complete_count,
        incomplete_whole_months=whole_count - complete_count,
        sliced_months=len(months) - whole_count,
        zero_observation_months=sum(m.observed_days == 0 for m in months),
        longest_complete_month_streak=longest_complete,
    )
    bins = [
        RunBin(label=label, runs=0, days=0)
        for label in ("1 day", "2–3 days", "4–7 days", "8–30 days", "31+ days")
    ]
    for run in runs:
        index = (
            0
            if run.days == 1
            else 1
            if run.days <= 3
            else 2
            if run.days <= 7
            else 3
            if run.days <= 30
            else 4
        )
        bins[index].runs += 1
        bins[index].days += run.days
    return summary, runs, months, bins


def read_missingness(
    session: Session,
    metric: str = "energy_generated",
    start_date: date | None = None,
    end_date: date | None = None,
    gap_page: int = 1,
    gap_page_size: int = 20,
    month_page: int = 1,
) -> MissingReport:
    definitions = {c[1]: c for c in DAILY_COLUMNS}
    if (
        metric not in definitions
        or not 1 <= gap_page <= 100000
        or not 1 <= month_page <= 100000
        or not 1 <= gap_page_size <= 50
    ):
        raise HTTPException(422, "Invalid metric or pagination")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "start_date must not be after end_date")
    eligible = canonical_query().cte("missing_canonical")
    first, last = session.execute(
        select(func.min(eligible.c.operational_date), func.max(eligible.c.operational_date))
    ).one()
    start = max(start_date or first, first) if first else None
    end = min(end_date or last, last) if last else None
    if start and start > end:
        start = end = None
    span = (end - start).days + 1 if start else 0
    if span > 20000:
        raise HTTPException(422, "Use a date window of at most 20000 calendar days")
    canonical_rows = (
        session.execute(
            select(eligible.c.operational_date, eligible.c.version_id)
            .where(eligible.c.operational_date.between(start, end))
            .order_by(eligible.c.operational_date)
            .limit(10001)
        ).all()
        if start
        else []
    )
    if len(canonical_rows) > 10000:
        raise HTTPException(422, "Use a narrower window with at most 10000 canonical dates")
    canonical = {row.operational_date for row in canonical_rows}
    values = {name: {} for name in definitions}
    fingerprints = []
    if canonical_rows:
        parts = []
        for table in TABLES:
            link = exists(
                select(VersionSource.version_id).where(
                    VersionSource.version_id == table.version_id,
                    VersionSource.source_id == table.source_id,
                )
            )
            parts.append(
                select(
                    eligible.c.operational_date.label("day"),
                    table.version_id.label("version_id"),
                    table.source_id.label("source_id"),
                    table.metric.label("metric"),
                    table.unit.label("unit"),
                    table.period.label("period"),
                    getattr(table, "fuel", literal(None, type_=String)).label("fuel"),
                    table.value.label("value"),
                    literal(table.__tablename__).label("source_table"),
                    link.label("source_linked"),
                )
                .join(eligible, table.version_id == eligible.c.version_id)
                .where(
                    eligible.c.operational_date.between(start, end),
                    table.zone == "national",
                    table.metric.in_(definitions),
                )
            )
        all_values = union_all(*parts).subquery("missing_values")
        rows = session.execute(
            select(all_values).order_by(
                all_values.c.day, all_values.c.metric, all_values.c.source_table
            )
        ).all()
        for row in rows:
            _, _, unit, period, fuel = definitions[row.metric]
            if (
                row.unit != unit
                or row.period != period
                or row.fuel != fuel
                or row.source_table != TABLE_FOR[row.metric].__tablename__
                or not row.source_linked
                or row.day in values[row.metric]
                or (row.value is not None and not row.value.is_finite())
            ):
                raise HTTPException(
                    503, "Missing-data assessment requires a measurement consistency review"
                )
            values[row.metric][row.day] = row.value
            fingerprints.append(
                (
                    row.day.isoformat(),
                    row.version_id,
                    row.source_id,
                    row.metric,
                    row.unit,
                    row.period,
                    row.fuel,
                    str(row.value),
                    row.source_table,
                )
            )
    summaries = []
    selected = runs = months = bins = None
    for name, column in definitions.items():
        summary, metric_runs, metric_months, metric_bins = analyse_metric(
            column, canonical, values[name], start, end
        )
        summaries.append(summary)
        if name == metric:
            selected, runs, months, bins = summary, metric_runs, metric_months, metric_bins
    next_steps = []
    if not selected.observed_days:
        next_steps.append("verify_metric_definition_and_original_source_coverage")
    if selected.missing_canonical_days:
        next_steps.append("investigate_manifest_quarantine_conflict_and_download_evidence")
    if selected.absent_field_days or selected.explicit_null_days:
        next_steps.append("compare_original_pdf_fields_with_parser_support_and_extraction")
    if selected.before_first_value_days or selected.after_last_value_days:
        next_steps.append("review_boundary_unavailability_before_choosing_analysis_window")
    if selected.internal_missing_days:
        next_steps.append("compare_justified_training_only_treatments_after_source_review")
    next_steps.append("preserve_zeroes_and_evaluate_only_genuinely_observed_test_targets")
    payload = {
        "rule": RULE_VERSION,
        "start": str(start),
        "end": str(end),
        "canonical": [(r.operational_date.isoformat(), r.version_id) for r in canonical_rows],
        "observations": fingerprints,
    }
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    offset = (gap_page - 1) * gap_page_size
    month_offset = (month_page - 1) * MONTH_PAGE_SIZE
    return MissingReport(
        generated_at=datetime.now(timezone.utc),
        earliest_canonical_date=first,
        latest_canonical_date=last,
        start_date=start,
        end_date=end,
        calendar_days=span,
        canonical_dates=len(canonical),
        missing_canonical_days=span - len(canonical),
        metrics=summaries,
        selected=selected,
        run_bins=bins,
        gap_page=gap_page,
        gap_page_size=gap_page_size,
        gap_total_pages=(len(runs) + gap_page_size - 1) // gap_page_size,
        gaps=runs[offset : offset + gap_page_size],
        month_page=month_page,
        month_total_pages=(len(months) + MONTH_PAGE_SIZE - 1) // MONTH_PAGE_SIZE,
        months=list(reversed(months))[month_offset : month_offset + MONTH_PAGE_SIZE],
        next_steps=next_steps,
        data_fingerprint=fingerprint,
    )


@router.get("/missingness", response_model=MissingReport)
def missingness(
    response: Response,
    session: Database,
    metric: MissingMetric = "energy_generated",
    start_date: date | None = None,
    end_date: date | None = None,
    gap_page: Annotated[int, Query(ge=1, le=100000)] = 1,
    gap_page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    month_page: Annotated[int, Query(ge=1, le=100000)] = 1,
) -> MissingReport:
    response.headers["Cache-Control"] = "no-store"
    return read_missingness(
        session, metric, start_date, end_date, gap_page, gap_page_size, month_page
    )
