"""Multivariable descriptive EDA over one canonical read-only snapshot."""

import hashlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import exists, select

from app.api.analytics import METRICS, number, percent, statistics
from app.api.monitoring import Database, canonical_query
from app.api.preparation import encode
from app.db.models import CostObservation, EnvironmentObservation, FuelObservation, VersionSource

router = APIRouter(prefix="/api/v1/analytics", tags=["Exploratory analysis"])
VARIABLES = {k: (*v[:4], None, v[4]) for k, v in METRICS.items()}
VARIABLES.update(
    {
        "maximum_temperature": (
            "Maximum temperature",
            EnvironmentObservation,
            "degC",
            "daily_maximum",
            None,
            False,
        ),
        "gas_supplied": ("Gas supplied", FuelObservation, "MMCFD", "daily", "gas", False),
        "production_cost_per_kwh": (
            "Production cost per kWh",
            CostObservation,
            "BDT/kWh",
            "daily",
            "all",
            False,
        ),
        "total_production_cost": (
            "Total production cost",
            CostObservation,
            "BDT",
            "daily",
            "all",
            False,
        ),
    }
)
DEFAULT = ["energy_generated", "evening_peak_generation", "evening_peak_demand"]
METHODS = {
    "sample": (
        "Current validated national measurements with linked source "
        "provenance; exploratory screening flags are not automatically "
        "removed."
    ),
    "missingness": (
        "No imputation. Pairwise complete calendar dates for relationships; "
        "complete consecutive dates for first differences."
    ),
    "quantiles": (
        "Type 7: linear interpolation at (n-1)*p; derived decimal summaries "
        "rounded to six places half-even."
    ),
    "boxplot": (
        "Quartiles and Tukey whiskers to most extreme observations within 1.5"
        " IQR. Outside values are review candidates, not confirmed errors."
    ),
    "moments": (
        "Sample variance/SD; bias-adjusted Fisher-Pearson skewness (n>=3), "
        "adjusted excess kurtosis (n>=4); unavailable for constant data."
    ),
    "relationships": (
        "Pearson and tie-adjusted Spearman, at least three paired dates and "
        "nonconstant inputs. Sample floor is not proof of adequacy. No "
        "p-values or causal interpretation."
    ),
    "change": (
        "Pearson on first calendar-day differences; each change requires "
        "original observations on both consecutive days for both variables."
    ),
    "lags": (
        "Pairwise Pearson at exact calendar lags 1-30, with separate paired "
        "counts. This is lagged association, not a missing-data-corrected "
        "classical ACF or forecast skill."
    ),
    "scaling": (
        "Display-only z scores use the selected window's observed mean/sample"
        " SD; not a train-only forecasting transform."
    ),
    "limitations": (
        "Different pairs may use different dates; the pairwise correlation "
        "matrix need not be positive semidefinite. Trends, seasonality, "
        "revisions and selective missingness can confound associations. "
        "Historical timing is not verified point-in-time availability."
    ),
}


def quantile(values, p):
    if not values:
        return None
    a = sorted(values)
    pos = Decimal(len(a) - 1) * Decimal(str(p))
    lo = int(pos)
    return a[lo] + (a[min(lo + 1, len(a) - 1)] - a[lo]) * (pos - lo)


def correlation(x, y):
    if len(x) < 3:
        return None, "insufficient_pairs"
    with localcontext() as ctx:
        ctx.prec = 50
        mx, my = sum(x) / len(x), sum(y) / len(y)
        xx = sum((v - mx) ** 2 for v in x)
        yy = sum((v - my) ** 2 for v in y)
        if not xx or not yy:
            return None, "constant_variable"
        r = sum((a - mx) * (b - my) for a, b in zip(x, y)) / (xx * yy).sqrt()
    return round(max(-1, min(1, float(r))), 8), "available"


def ranks(values):
    result = [Decimal(0)] * len(values)
    positions = sorted(range(len(values)), key=values.__getitem__)
    i = 0
    while i < len(positions):
        j = i + 1
        while j < len(positions) and values[positions[j]] == values[positions[i]]:
            j += 1
        rank = Decimal(i + 1 + j) / 2
        for index in positions[i:j]:
            result[index] = rank
        i = j
    return result


def describe(values):
    valid = [v for v in values if v is not None]
    n = len(valid)
    base = statistics(valid, False).model_dump()
    q = [quantile(valid, p) for p in (0.05, 0.25, 0.5, 0.75, 0.95)]
    mean = sum(valid) / n if n else None
    variance = sum((v - mean) ** 2 for v in valid) / (n - 1) if n > 1 else None
    iqr = q[3] - q[1] if n else None
    low, high = (q[1] - Decimal("1.5") * iqr, q[3] + Decimal("1.5") * iqr) if n else (None, None)
    inside = [v for v in valid if low <= v <= high] if n else []
    skew = kurt = None
    if variance and n >= 3:
        sd = variance.sqrt()
        skew = Decimal(n) * sum(((v - mean) / sd) ** 3 for v in valid) / ((n - 1) * (n - 2))
    if variance and n >= 4:
        kurt = Decimal(n * (n + 1)) * sum(((v - mean) / variance.sqrt()) ** 4 for v in valid) / (
            (n - 1) * (n - 2) * (n - 3)
        ) - Decimal(3 * (n - 1) ** 2) / ((n - 2) * (n - 3))
    runs, current = [], 0
    for v in values:
        if v is None:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return {
        **base,
        "missing_days": len(values) - n,
        "coverage_percent": percent(n, len(values)),
        "negative_days": sum(v < 0 for v in valid),
        "variance": number(variance),
        "range": number(max(valid) - min(valid)) if n else None,
        "p05": number(q[0]),
        "q1": number(q[1]),
        "q3": number(q[3]),
        "p95": number(q[4]),
        "iqr": number(iqr),
        "lower_fence": number(low),
        "upper_fence": number(high),
        "whisker_low": number(min(inside)) if inside else None,
        "whisker_high": number(max(inside)) if inside else None,
        "iqr_outside_days": sum(v < low or v > high for v in valid) if n else 0,
        "cv_percent": number(100 * variance.sqrt() / mean)
        if variance is not None and mean > 0
        else None,
        "adjusted_skewness": number(skew),
        "adjusted_excess_kurtosis": number(kurt),
        "longest_missing_run": max(runs, default=0),
    }


def relationships(columns):
    result = []
    for i, (name, x) in enumerate(columns.items()):
        for other, y in list(columns.items())[i:]:
            paired = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
            a, b = ([v[0] for v in paired], [v[1] for v in paired])
            r, status = correlation(a, b)
            rho, _ = correlation(ranks(a), ranks(b))
            changes = [
                (x[t] - x[t - 1], y[t] - y[t - 1])
                for t in range(1, len(x))
                if all(v is not None for v in (x[t], x[t - 1], y[t], y[t - 1]))
            ]
            change_r, change_status = correlation([v[0] for v in changes], [v[1] for v in changes])
            slope = intercept = None
            if r is not None:
                mx, my = sum(a) / len(a), sum(b) / len(b)
                slope = sum((v - mx) * (w - my) for v, w in paired) / sum((v - mx) ** 2 for v in a)
                intercept = my - slope * mx
            result.append(
                {
                    "x": name,
                    "y": other,
                    "n": len(paired),
                    "pearson": r,
                    "spearman": rho,
                    "status": status,
                    "change_n": len(changes),
                    "change_pearson": change_r,
                    "change_status": change_status,
                    "slope_y_on_x": number(slope),
                    "intercept_y_on_x": number(intercept),
                }
            )
    return result


def build_eda(dates, columns, meta, source_ids, generated_at=None):
    rows = [
        {
            "date": d.isoformat(),
            **{k: str(v[i]) if v[i] is not None else None for k, v in columns.items()},
        }
        for i, d in enumerate(dates)
    ]
    variables = []
    for key, values in columns.items():
        lags = []
        for lag in range(1, min(30, len(dates) - 1) + 1):
            pairs = [
                (values[t - lag], values[t])
                for t in range(lag, len(values))
                if values[t - lag] is not None and values[t] is not None
            ]
            r, status = correlation([p[0] for p in pairs], [p[1] for p in pairs])
            lags.append({"lag": lag, "n": len(pairs), "r": r, "status": status})
        variables.append(
            {
                "key": key,
                **meta[key],
                "statistics": {
                    **describe(values),
                    **({"cv_percent": None} if meta[key]["unit"] == "degC" else {}),
                },
                "lags": lags,
            }
        )
    complete = sum(all(columns[k][i] is not None for k in columns) for i in range(len(dates)))
    report = {
        "schema": "multivariate_eda_v1",
        "start_date": dates[0].isoformat() if dates else None,
        "end_date": dates[-1].isoformat() if dates else None,
        "calendar_days": len(dates),
        "complete_case_days": complete,
        "variables": variables,
        "relationships": relationships(columns),
        "rows": rows,
        "methods": METHODS,
        "source_fingerprint": hashlib.sha256(encode(source_ids)).hexdigest(),
        "lineage": sorted(set(tuple(x[:3]) for x in source_ids)),
    }
    report["analysis_id"] = hashlib.sha256(encode(report)).hexdigest()
    report["generated_at"] = generated_at or datetime.now(timezone.utc).isoformat()
    return report


def read_eda(session, metrics, start_date=None, end_date=None):
    if (
        not 1 <= len(metrics) <= 8
        or len(set(metrics)) != len(metrics)
        or any(k not in VARIABLES for k in metrics)
    ):
        raise HTTPException(422, "Select one to eight distinct supported variables")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "Start date must not exceed end date")
    eligible = canonical_query().cte("eda_canonical")
    all_rows = session.execute(
        select(eligible.c.operational_date, eligible.c.version_id).order_by(
            eligible.c.operational_date
        )
    ).all()
    start = max(start_date or all_rows[0][0], all_rows[0][0]) if all_rows else None
    end = min(end_date or all_rows[-1][0], all_rows[-1][0]) if all_rows else None
    dates = []
    if start and start <= end:
        if (end - start).days >= 10000:
            raise HTTPException(422, "Select at most 10,000 calendar days")
        dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    columns = {k: [None] * len(dates) for k in metrics}
    positions = {d: i for i, d in enumerate(dates)}
    sources = []
    for table in {VARIABLES[k][1] for k in metrics}:
        names = [k for k in metrics if VARIABLES[k][1] == table]
        if not dates:
            continue
        linked = exists(
            select(VersionSource.version_id).where(
                VersionSource.version_id == table.version_id,
                VersionSource.source_id == table.source_id,
            )
        )
        rows = session.execute(
            select(eligible.c.operational_date, table, linked.label("linked"))
            .join(eligible, table.version_id == eligible.c.version_id)
            .where(
                eligible.c.operational_date.between(start, end),
                table.metric.in_(names),
                table.zone == "national",
            )
            .order_by(eligible.c.operational_date, table.id)
        ).all()
        seen = set()
        for day, row, source_linked in rows:
            _, _, unit, period, fuel, _ = VARIABLES[row.metric]
            if getattr(row, "fuel", None) != fuel:
                continue
            key = (day, row.metric)
            if (
                key in seen
                or row.unit != unit
                or row.period != period
                or not source_linked
                or (row.value is not None and not row.value.is_finite())
            ):
                raise HTTPException(503, "EDA measurements require consistency review")
            seen.add(key)
            columns[row.metric][positions[day]] = row.value
            sources.append(
                (
                    day.isoformat(),
                    str(row.version_id),
                    str(row.source_id),
                    row.metric,
                    str(row.value),
                )
            )
    meta = {
        k: {
            "label": VARIABLES[k][0],
            "unit": VARIABLES[k][2],
            "period": VARIABLES[k][3],
            "source_support": "legacy_and_modern" if VARIABLES[k][5] else "modern_layout",
        }
        for k in metrics
    }
    return build_eda(dates, columns, meta, sorted(sources))


@router.get("/exploratory")
def exploratory(
    response: Response,
    session: Database,
    metric: Annotated[list[str] | None, Query()] = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    response.headers["Cache-Control"] = "no-store"
    with localcontext() as context:
        context.prec = 50
        report = read_eda(session, metric or DEFAULT, start_date, end_date)
        data = encode(report)
        if len(data) > 3_500_000:
            raise HTTPException(422, "Analysis exceeds hosted size limit; narrow the date range")
        return Response(data, media_type="application/json", headers={"Cache-Control": "no-store"})
