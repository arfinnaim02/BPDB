"""Read-only physical consistency and heuristic screening; flags are not corrections."""

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.api.analytics import METRICS
from app.api.monitoring import Database, canonical_query
from app.db.models import GenerationObservation, SourceDocument, VersionSource

router = APIRouter(prefix="/api/v1/dataset", tags=["Measurement review"])
RULE_VERSION = "national_energy_screen_v1"
LOW_RATIO = Decimal("0.10")
FIELDS = (
    "energy_generated",
    "maximum_generation",
    "minimum_generation",
    "day_peak_generation",
    "evening_peak_generation",
)


class ReviewMeasurement(BaseModel):
    metric: str
    value: str | None
    unit: str
    period: str
    source_id: str
    source_page: int | None
    raw_text: str | None
    source_url: str | None
    source_sha256: str | None
    source_linked: bool


class ReviewFlag(BaseModel):
    code: str
    kind: str
    explanation: str


class ReviewDay(BaseModel):
    operational_date: date
    version_id: str
    flags: list[ReviewFlag]
    measurements: list[ReviewMeasurement]
    energy_to_peak_ratio: str | None


class ReviewReport(BaseModel):
    generated_at: datetime
    rule_version: str = RULE_VERSION
    scope: str = "Current validated national generation/energy records only"
    canonical_dates: int
    energy_peak_pairs: int
    flagged_dates: int
    flag_counts: dict[str, int]
    page: int
    page_size: int
    total_pages: int
    items: list[ReviewDay]
    data_fingerprint: str
    limitation: str = (
        "Screening is not original-PDF verification or a model eligibility certificate. "
        "The low-ratio rule is an explicit review heuristic, not a validated BPDB threshold. "
        "No value, quality status, canonical pointer or review decision is changed. "
        "An empty queue does not prove extraction accuracy. Other metrics are outside this screen."
    )


def screen(values: dict[str, Decimal]) -> tuple[list[ReviewFlag], str | None]:
    """Only compare like national daily definitions; retain every source value."""
    flags = []

    def flag(code, kind, explanation):
        flags.append(ReviewFlag(code=code, kind=kind, explanation=explanation))

    for metric, value in values.items():
        if value < 0 or (metric != "minimum_generation" and value == 0):
            flag(
                "non_positive_core_value",
                "consistency",
                f"{metric} is non-positive; inspect its source.",
            )
    peak = values.get("maximum_generation")
    energy = values.get("energy_generated")
    minimum = values.get("minimum_generation")
    if peak is not None:
        for name in ("day_peak_generation", "evening_peak_generation", "minimum_generation"):
            if name in values and values[name] > peak + Decimal("1"):
                flag(
                    "generation_above_daily_maximum",
                    "consistency",
                    f"{name} exceeds the reported daily maximum by more than 1 MW.",
                )
    ratio = None
    with localcontext() as context:
        context.prec = 50
        if energy is not None and peak is not None and peak > 0:
            ceiling = peak * Decimal(24) / Decimal(1000)
            tolerance = max(Decimal("0.1"), ceiling * Decimal("0.001"))
            ratio_value = energy / ceiling
            ratio = format(ratio_value.quantize(Decimal("0.000001")), "f")
            if energy > ceiling + tolerance:
                flag(
                    "energy_above_peak_daily_ceiling",
                    "consistency",
                    "Daily energy exceeds maximum MW × 24 / 1000, beyond the rounding tolerance.",
                )
            if 0 <= ratio_value < LOW_RATIO:
                flag(
                    "low_energy_to_peak_ratio",
                    "heuristic",
                    "Energy / (maximum MW × 24 / 1000) is below 0.10. "
                    "This prioritizes source review; it does not establish an error.",
                )
        if energy is not None and minimum is not None and minimum >= 0:
            floor = minimum * Decimal(24) / Decimal(1000)
            tolerance = max(Decimal("0.1"), floor * Decimal("0.001"))
            if energy < floor - tolerance:
                flag(
                    "energy_below_minimum_daily_floor",
                    "consistency",
                    "Daily energy is below minimum MW × 24 / 1000, beyond the rounding "
                    "tolerance; verify that the reported definitions align.",
                )
    return flags, ratio


def read_review(
    session: Session,
    page: int = 1,
    page_size: int = 20,
    start_date: date | None = None,
    end_date: date | None = None,
) -> ReviewReport:
    if not 1 <= page <= 100000 or not 1 <= page_size <= 50:
        raise HTTPException(422, "Invalid review pagination")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "start_date must not be after end_date")
    query = canonical_query()
    if start_date:
        query = query.where(query.selected_columns.operational_date >= start_date)
    if end_date:
        query = query.where(query.selected_columns.operational_date <= end_date)
    eligible = query.cte("review_canonical")
    canonical = session.execute(
        select(eligible.c.operational_date, eligible.c.version_id)
        .order_by(eligible.c.operational_date)
        .limit(10001)
    ).all()
    if len(canonical) > 10000:
        raise HTTPException(422, "Select a narrower review date range")
    table = GenerationObservation
    linked = exists(
        select(VersionSource.version_id).where(
            VersionSource.version_id == table.version_id,
            VersionSource.source_id == table.source_id,
        )
    )
    rows = (
        session.execute(
            select(
                eligible.c.operational_date,
                table,
                SourceDocument.original_url,
                SourceDocument.sha256,
                linked.label("source_linked"),
            )
            .select_from(table)
            .join(eligible, eligible.c.version_id == table.version_id)
            .outerjoin(SourceDocument, SourceDocument.id == table.source_id)
            .where(table.zone == "national", table.metric.in_(FIELDS))
            .order_by(eligible.c.operational_date, table.metric, table.id)
        ).all()
        if canonical
        else []
    )
    grouped = defaultdict(list)
    fingerprint_rows = []
    for day, measurement, url, checksum, source_linked in rows:
        grouped[day].append(
            ReviewMeasurement(
                metric=measurement.metric,
                value=str(measurement.value) if measurement.value is not None else None,
                unit=measurement.unit,
                period=measurement.period,
                source_id=measurement.source_id,
                source_page=measurement.source_page,
                raw_text=(measurement.raw_text or "")[:1000] or None,
                source_url=url,
                source_sha256=checksum,
                source_linked=bool(source_linked),
            )
        )
        fingerprint_rows.append(
            (
                day.isoformat(),
                measurement.version_id,
                measurement.metric,
                str(measurement.value),
                measurement.unit,
                measurement.period,
                measurement.source_id,
                checksum,
                bool(source_linked),
            )
        )
    flagged = []
    pairs = 0
    counts = Counter()
    for day, version_id in canonical:
        measurements = grouped[day]
        flags = []
        values = {}
        frequencies = Counter(m.metric for m in measurements)
        for m in measurements:
            _, _, unit, period, _ = METRICS[m.metric]
            if (
                frequencies[m.metric] > 1
                or m.unit != unit
                or m.period != period
                or not m.source_linked
            ):
                flags.append(
                    ReviewFlag(
                        code="measurement_dimension_or_provenance",
                        kind="consistency",
                        explanation=f"{m.metric} has duplicate, unexpected dimensions "
                        "or an absent version-source link.",
                    )
                )
                continue
            if m.value is not None:
                value = Decimal(m.value)
                if not value.is_finite():
                    flags.append(
                        ReviewFlag(
                            code="non_finite_measurement",
                            kind="consistency",
                            explanation=f"{m.metric} is not finite.",
                        )
                    )
                else:
                    values[m.metric] = value
        pairs += int(
            "energy_generated" in values
            and "maximum_generation" in values
            and values["maximum_generation"] > 0
        )
        checks, ratio = screen(values)
        flags.extend(checks)
        if flags:
            # A date counts once for each rule, even if several measurements trigger it.
            flags = list({flag.code: flag for flag in flags}.values())
            counts.update(flag.code for flag in flags)
            flagged.append(
                ReviewDay(
                    operational_date=day,
                    version_id=version_id,
                    flags=flags,
                    measurements=measurements,
                    energy_to_peak_ratio=ratio,
                )
            )
    payload = {
        "rules": RULE_VERSION,
        "low_ratio": str(LOW_RATIO),
        "start": str(start_date),
        "end": str(end_date),
        "canonical": [(d.isoformat(), v) for d, v in canonical],
        "rows": fingerprint_rows,
    }
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    offset = (page - 1) * page_size
    return ReviewReport(
        generated_at=datetime.now(timezone.utc),
        canonical_dates=len(canonical),
        energy_peak_pairs=pairs,
        flagged_dates=len(flagged),
        flag_counts=dict(sorted(counts.items())),
        page=page,
        page_size=page_size,
        total_pages=(len(flagged) + page_size - 1) // page_size,
        items=flagged[offset : offset + page_size],
        data_fingerprint=fingerprint,
    )


@router.get("/measurement-review", response_model=ReviewReport)
def measurement_review(
    response: Response,
    session: Database,
    page: Annotated[int, Query(ge=1, le=100000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    start_date: date | None = None,
    end_date: date | None = None,
) -> ReviewReport:
    response.headers["Cache-Control"] = "no-store"
    return read_review(session, page, page_size, start_date, end_date)
