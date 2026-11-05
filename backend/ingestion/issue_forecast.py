"""Issue tomorrow's saved-model research forecast and reconcile recent outcomes."""

import argparse
import json
from datetime import timedelta
from pathlib import Path

from app.db.models import ResearchForecast
from app.db.session import session_factory
from app.services.forecasting import (
    DHAKA,
    build_issue,
    capture_clock,
    capture_days,
    loaded_model,
    retain_issue,
    retain_outcome,
)
from sqlalchemy import select, text

ROOT = Path(__file__).resolve().parents[2]


def execute(factory, apply=False):
    model, card = loaded_model()
    with factory() as session:
        if session.get_bind().dialect.name == "postgresql":
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            session.execute(text("SET LOCAL statement_timeout = '30000'"))
        captured = capture_clock(session)
        today = captured.astimezone(DHAKA).date()
        target = today + timedelta(days=1)
        snapshot = capture_days(
            session, target - timedelta(days=35), target - timedelta(days=2), captured
        )
        issued = capture_clock(session)
        issue = build_issue(snapshot, model, card, captured, issued)
        outcome_count = 0
        if apply:
            record, inserted = retain_issue(session, issue)
            forecasts = session.scalars(
                select(ResearchForecast)
                .where(
                    ResearchForecast.status == "forecast",
                    ResearchForecast.target_date < today,
                    ResearchForecast.target_date >= today - timedelta(days=90),
                )
                .order_by(ResearchForecast.target_date.desc())
                .limit(2001)
            ).all()
            if len(forecasts) > 2000:
                raise ValueError("Outcome reconciliation safety cap reached")
            if forecasts:
                actuals = capture_days(
                    session,
                    min(f.target_date for f in forecasts),
                    max(f.target_date for f in forecasts),
                    captured,
                )
                by_date = {r["date"]: r for r in actuals}
                outcome_count = sum(
                    retain_outcome(session, f, by_date[str(f.target_date)], captured)
                    for f in forecasts
                )
            session.commit()
            result = {
                "mode": "applied",
                "inserted": inserted,
                "id": record.id,
                "target_date": str(record.target_date),
                "issued_at": record.issued_at.isoformat(),
                "status": record.status,
                "prediction": str(record.prediction) if record.prediction is not None else None,
                "reason": record.payload["reason"],
                "model_id": record.model_id,
                "model_experiment_id": record.model_experiment_id,
                "new_outcome_comparisons": outcome_count,
            }
        else:
            result = {
                "mode": "preview",
                "target_date": str(issue["target_date"]),
                "status": issue["status"],
                "prediction": str(issue["prediction"]) if issue["prediction"] is not None else None,
                "reason": issue["payload"]["reason"],
                "model_id": card["model_id"],
                "note": "Read-only preview; no forecast has been issued or retained",
            }
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        result = execute(session_factory(), args.apply)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}), flush=True)
        return 1
    output = ROOT / "data/forecasts"
    output.mkdir(parents=True, exist_ok=True)
    (output / "latest_run.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
