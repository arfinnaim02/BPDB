"""Validate/preview the registered experiment. This module never fits or forecasts."""

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from app.api.preparation import encode

from research.treatment_study import BUNDLE_SHA, SNAPSHOT_ID

PATH = Path(__file__).resolve().parents[2] / "docs/TREATMENT_IMPACT_PROTOCOL.json"


def validate(protocol):
    if protocol["source"]["bundle_sha256"] != BUNDLE_SHA:
        raise ValueError("Frozen source differs")
    if protocol["source"]["snapshot_id"] != SNAPSHOT_ID:
        raise ValueError("Snapshot differs")
    if protocol["scope"]["excluded_years"] != [2025] or protocol["results"] is not None:
        raise ValueError("Previously evaluated year/results must remain excluded")
    if set(protocol["policies"]) != {
        "observed_only",
        "seasonal_original_7",
        "past_original_3",
    }:
        raise ValueError("Undeclared treatment")
    for key, value in protocol["safety"].items():
        if value != 0:
            raise ValueError("Registration must not authorize execution: " + key)
    h = protocol["historical_design"]
    if len(h["folds"]) != 3 or h["parameter_search"] or h["refit_within_fold"]:
        raise ValueError("Diagnostic folds/search differ")
    if [r["target_start"] for r in h["folds"]] != ["2021-01-01", "2022-01-01", "2023-01-01"]:
        raise ValueError("Diagnostic target years differ")
    for row in (*h["folds"], h["secondary_window"]):
        start, end = map(date.fromisoformat, (row["target_start"], row["target_end"]))
        first, stop = map(date.fromisoformat, (row["fit_start"], row["fit_stop"]))
        if not (
            first == date(2020, 1, 1)
            and first <= stop
            and stop == start - timedelta(days=2)
            and start <= end <= date(2024, 12, 31)
            and start.year == end.year
        ):
            raise ValueError("Chronological fold boundary or embargo invalid")
    future = protocol["prospective_confirmation"]
    if not (
        date.fromisoformat(future["target_start"]) > date(2026, 11, 8)
        and future["status"] == "planned_not_started_no_schedule_created"
        and future["minimum_affected_common_dates"] > 0
        and (
            date.fromisoformat(future["target_end"]) - date.fromisoformat(future["target_start"])
        ).days
        == 29
    ):
        raise ValueError("Prospective reservation differs")
    return hashlib.sha256(encode(protocol)).hexdigest()


def main():
    protocol = json.loads(PATH.read_text())
    print(
        json.dumps(
            {
                "status": "pre_registered_execution_not_started",
                "protocol_sha256": validate(protocol),
                "historical_folds": protocol["historical_design"]["folds"],
                "prospective_window": {
                    key: protocol["prospective_confirmation"][key]
                    for key in ("target_start", "target_end", "first_issue", "status")
                },
                "models_fit": 0,
                "database_writes": 0,
                "results": None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
