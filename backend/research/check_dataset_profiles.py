"""One read-only live coverage-plan acceptance check; never fit or prepare data."""

import json
from contextlib import contextmanager
from pathlib import Path

from app.api.dataset_profiles import build_profiles
from app.api.monitoring import read_session
from app.api.preparation import encode
from app.api.quality import read_quality
from sqlalchemy import text


def main():
    out = Path(__file__).resolve().parents[2] / "data/research_dataset_profiles"
    out.mkdir(parents=True, exist_ok=True)
    with contextmanager(read_session)() as session:
        if session.get_bind().dialect.name != "postgresql":
            raise ValueError("Live check requires PostgreSQL")
        if session.scalar(text("SHOW transaction_read_only")) != "on":
            raise ValueError("Read-only transaction required")
        report = build_profiles(read_quality(session, gap_page=1, gap_page_size=1))
    if (
        len(report["variables"]) != 13
        or sum(v["long_history_candidate"] for v in report["variables"]) != 5
    ):
        raise ValueError("Unexpected metric catalog")
    if any(p["joint_complete_eligible_dates"] is not None for p in report["profiles"]):
        raise ValueError("Coverage alone cannot approve joint modelling rows")
    if any(v["modern_missing_calendar_days"] < 0 for v in report["variables"]):
        raise ValueError("Calendar denominator differs")
    if report["models_fit"] != 0 or report["database_writes"] != 0:
        raise ValueError("No fitting or writes authorized")
    (out / "profiles.json").write_bytes(encode(report))
    checks = {
        "status": "passed",
        "postgresql_transaction_read_only": True,
        "variables": len(report["variables"]),
        "core_variables": 5,
        "modern_boundary_status": "proposed_not_universal_publication_proof",
        "joint_model_eligibility": "not_assessed_not_approved",
        "database_writes": 0,
        "models_fit": 0,
        "coverage_assessment_id": report["coverage_assessment_id"],
        "coverage": [
            {
                k: v[k]
                for k in (
                    "metric",
                    "earliest_observed_date",
                    "full_history_observed_days",
                    "modern_observed_days",
                    "modern_calendar_days",
                    "modern_calendar_coverage_percent",
                )
            }
            for v in report["variables"]
        ],
    }
    (out / "verification.json").write_bytes(encode(checks))
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit("Dataset goal acceptance failed: " + type(exc).__name__) from None
