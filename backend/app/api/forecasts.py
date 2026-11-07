"""Read-only prospective research forecasts; original master data stays separate."""

import csv
import io
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select

from app.api.monitoring import Database
from app.db.models import ResearchForecast, ResearchForecastOutcome
from app.services.forecasting import DHAKA, iso, loaded_model

router = APIRouter(prefix="/api/v1", tags=["Research forecasts"])
LIMITATION = (
    "Saved OLS research outputs, not official BPDB observations or verified operational forecasts. "
    "Inputs are captured before actual issuance; official publication times can remain unknown. "
    "Historical final-test accuracy does not guarantee future accuracy."
)


def outcome_dict(row):
    return (
        {
            "observed": str(row.observed),
            "signed_error": str(row.signed_error),
            "absolute_error": str(row.absolute_error),
            "actual_version_id": row.actual_version_id,
            "source_id": row.source_id,
            "compared_at": iso(row.created_at),
            "lineage": row.lineage,
        }
        if row
        else None
    )


def outcomes_for(session, ids):
    result = {}
    for row in session.scalars(
        select(ResearchForecastOutcome)
        .where(ResearchForecastOutcome.forecast_id.in_(ids))
        .order_by(ResearchForecastOutcome.created_at.desc(), ResearchForecastOutcome.id.desc())
    ):
        result.setdefault(row.forecast_id, row)
    return result


def row_dict(row, outcome=None):
    return {
        "id": row.id,
        "model_id": row.model_id,
        "model_experiment_id": row.model_experiment_id,
        "target_date": str(row.target_date),
        "issued_at": iso(row.issued_at),
        "status": row.status,
        "prediction": str(row.prediction) if row.prediction is not None else None,
        "input_fingerprint": row.input_fingerprint,
        "reason": row.payload.get("reason"),
        "latest_donor": row.payload.get("latest_donor"),
        "substituted_slots": row.payload.get("substituted_slots", 0),
        "unknown_official_time_slots": row.payload.get("unknown_official_time_slots", 0),
        "outcome": outcome_dict(outcome),
    }


def read_history(session, limit, now=None, *, include_evidence=False):
    _, card = loaded_model()
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(DHAKA).date()
    rows = session.scalars(
        select(ResearchForecast)
        .where(ResearchForecast.model_id == card["model_id"])
        .order_by(ResearchForecast.issued_at.desc(), ResearchForecast.id.desc())
        .limit(limit)
    ).all()
    comparisons = outcomes_for(session, [r.id for r in rows])
    recent = session.scalars(
        select(ResearchForecast)
        .where(
            ResearchForecast.model_id == card["model_id"],
            ResearchForecast.target_date < today,
            ResearchForecast.target_date >= today - timedelta(days=90),
        )
        .order_by(ResearchForecast.issued_at, ResearchForecast.id)
        .limit(2001)
    ).all()
    if len(recent) > 2000:
        raise HTTPException(503, "Prospective summary safety cap reached")
    # Never cherry-pick the best later reissue: earliest successful issue per target.
    first = {}
    for r in recent:
        if r.status == "forecast":
            first.setdefault(r.target_date, r)
    latest = outcomes_for(session, [r.id for r in first.values()])
    errors = [float(latest[r.id].signed_error) for r in first.values() if r.id in latest]
    summary = {
        "window_start": str(today - timedelta(days=90)),
        "window_end": str(today - timedelta(days=1)),
        "completed_targets_attempted": len({r.target_date for r in recent}),
        "completed_targets_with_forecast": len(first),
        "scored_dates": len(errors),
        "mae": sum(abs(e) for e in errors) / len(errors) if errors else None,
        "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)) if errors else None,
        "bias": sum(errors) / len(errors) if errors else None,
        "selection_rule": (
            "Earliest successful issue per model/target; latest retained actual revision"
        ),
    }
    report = {
        "generated_at": iso(now),
        "model": card,
        "items": [row_dict(r, comparisons.get(r.id)) for r in rows],
        "limit": limit,
        "summary": summary,
        "limitation": LIMITATION,
        "outcome_scope": (
            "Latest retained comparisons, reconciled after collection "
            "over the previous 90 completed days"
        ),
    }
    if include_evidence:
        report["summary_evidence"] = [row_dict(r, latest.get(r.id)) for r in first.values()]
        report["attempted_target_dates"] = sorted({str(r.target_date) for r in recent})
    return report


def history_csv(report):
    out = io.StringIO(newline="")
    w = csv.writer(out)
    w.writerow(
        [
            "Target Date",
            "Actual Issue Time (UTC)",
            "Status",
            "Predicted Energy (million kWh)",
            "Latest Retained Actual (million kWh)",
            "Signed Error (million kWh)",
            "Absolute Error (million kWh)",
            "Model ID",
            "Input Fingerprint",
            "Withheld Reason",
        ]
    )
    for r in report["items"]:
        actual = r["outcome"] or {}
        w.writerow(
            [
                r["target_date"],
                r["issued_at"],
                r["status"],
                r["prediction"],
                actual.get("observed"),
                actual.get("signed_error"),
                actual.get("absolute_error"),
                r["model_id"],
                r["input_fingerprint"],
                r["reason"],
            ]
        )
    return out.getvalue().encode("utf-8-sig")


@router.get("/forecasts")
def forecasts(
    response: Response,
    session: Database,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    download: Literal["csv"] | None = None,
):
    report = read_history(session, limit)
    response.headers["Cache-Control"] = "no-store"
    if download:
        return Response(
            history_csv(report),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="bpdb-research-forecast-history.csv"',
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    return report


@router.get("/forecasts/{forecast_id}")
def forecast_detail(forecast_id: str, session: Database):
    if len(forecast_id) != 64 or any(c not in "0123456789abcdef" for c in forecast_id):
        raise HTTPException(422, "Invalid forecast identifier")
    row = session.get(ResearchForecast, forecast_id)
    if row is None:
        raise HTTPException(404, "Forecast not found")
    result = row_dict(row, outcomes_for(session, [row.id]).get(row.id))
    result.update(payload=row.payload, limitation=LIMITATION)
    return Response(
        content=json.dumps(result),
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )
