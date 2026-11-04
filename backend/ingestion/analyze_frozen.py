"""Descriptive energy analysis from a verified immutable research bundle."""

import argparse
import gzip
import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

from app.api.preparation import encode

from ingestion.freeze_research import verify_bundle, verify_repairs

RULE = "frozen_energy_descriptive_v1"
PINNED_SNAPSHOT = "4f35dcb7da194025f79f2f7fb8ed52066e599c96f72e7cd0fc62c691fb4883a1"


def decimal_display(value):
    if value is None:
        return None
    with localcontext() as context:
        context.prec = 40
        return str(value.quantize(Decimal("0.000001")))


def describe(values):
    values = sorted(values)
    if not values:
        return dict(mean=None, median=None, minimum=None, maximum=None, sample_sd=None)
    with localcontext() as context:
        context.prec = 40
        mean = sum(values) / len(values)
        middle = len(values) // 2
        median = values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2
        sd = (
            (sum((v - mean) ** 2 for v in values) / (len(values) - 1)).sqrt()
            if len(values) > 1
            else None
        )
        return {
            k: decimal_display(v)
            for k, v in dict(
                mean=mean, median=median, minimum=values[0], maximum=values[-1], sample_sd=sd
            ).items()
        }


def group_rows(rows, key, *, totals=True):
    groups = defaultdict(list)
    for row in rows:
        groups[key(row)].append(row)
    output = []
    for label, items in sorted(groups.items()):
        usable = [Decimal(r["original_value"]) for r in items if r["eligible"]]
        complete = len(usable) == len(items)
        output.append(
            {
                "label": label,
                "calendar_days": len(items),
                "observed_days": sum(r["original_value"] is not None for r in items),
                "eligible_days": len(usable),
                "held_days": sum(r["review_hold"] for r in items),
                "missing_days": sum(r["original_value"] is None for r in items),
                "coverage_percent": decimal_display(Decimal(100) * len(usable) / len(items)),
                "complete": complete,
                **describe(usable),
                "complete_total": decimal_display(sum(usable)) if complete and totals else None,
            }
        )
    return output


def analyze(data):
    manifest, original, audit = verify_bundle(data)
    if manifest["snapshot_id"] != PINNED_SNAPSHOT:
        raise ValueError("This release requires the independently accepted snapshot")
    repairs = verify_repairs(original)
    originals = {d["operational_date"]: d for d in original}
    rows = []
    for item in audit:
        source_day = originals.get(item["operational_date"])
        measurements = (
            [m for m in source_day["measurements"] if m["metric"] == "energy_generated"]
            if source_day
            else []
        )
        m = measurements[0] if measurements else None
        source = (
            next((s for s in source_day["sources"] if s["id"] == m["source_id"]), None)
            if m
            else None
        )
        rows.append(
            {
                "date": item["operational_date"],
                "split": item["split"],
                "state": item["state"],
                "original_value": item["original_value"] or None,
                "eligible": item["observed_target_candidate"] == "True",
                "review_hold": item["review_hold"] == "True",
                "review_flags": item["review_flags"],
                "version_id": item["version_id"] or None,
                "source_url": source["url"] if source else None,
                "source_sha256": source["sha256"] if source else None,
                "trailing_7_mean": None,
            }
        )
    for i, row in enumerate(rows):
        window = rows[max(0, i - 6) : i + 1]
        if len(window) == 7 and all(r["eligible"] for r in window):
            row["trailing_7_mean"] = decimal_display(
                sum(Decimal(r["original_value"]) for r in window) / 7
            )
    monthly = group_rows(rows, lambda r: r["date"][:7])
    for i, month in enumerate(monthly):
        month["mom_total_percent"] = None
        month["change_status"] = "no_previous_month" if i == 0 else "incomplete_months"
        if i and month["complete"] and monthly[i - 1]["complete"]:
            previous = Decimal(monthly[i - 1]["complete_total"])
            if previous:
                month["mom_total_percent"] = decimal_display(
                    (Decimal(month["complete_total"]) / previous - 1) * 100
                )
                month["change_status"] = "two_complete_months"
            else:
                month["change_status"] = "zero_previous_total"
    weekdays = group_rows(
        rows, lambda r: str(date.fromisoformat(r["date"]).weekday()), totals=False
    )
    for group in weekdays:
        group["label"] = (
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        )[int(group["label"])]
    report = {
        "rule_version": RULE,
        "snapshot_id": manifest["snapshot_id"],
        "source_bundle_sha256": hashlib.sha256(data).hexdigest(),
        "scope": "Frozen 2024 national energy generation; descriptive observed-data analysis",
        "unit": "million_kWh",
        "config": manifest["config"],
        "splits": manifest["splits"],
        "repaired_dates": repairs,
        "calendar_days": len(rows),
        "observed_days": sum(r["original_value"] is not None for r in rows),
        "eligible_days": sum(r["eligible"] for r in rows),
        "held_days": sum(r["review_hold"] for r in rows),
        "missing_days": sum(r["original_value"] is None for r in rows),
        "statistics": describe([Decimal(r["original_value"]) for r in rows if r["eligible"]]),
        "daily": rows,
        "monthly": monthly,
        "quarterly": group_rows(rows, lambda r: "2024-Q" + str((int(r["date"][5:7]) - 1) // 3 + 1)),
        "weekday": weekdays,
        "limitations": [
            "One year describes monthly patterns; it does not establish recurring seasonality.",
            "Missing and review-held days do not enter descriptive statistics or rolling means.",
            "Incomplete months and quarters have no complete-period energy total "
            "or percent change.",
            "Seven-day means require all seven consecutive calendar days observed and unheld.",
            "Weekday groups have different date composition; differences are not "
            "causal weekday effects.",
            "No values are estimated, no forecasts are fitted, and these are not "
            "point-in-time backtests.",
            "Validation/test values are visible for descriptive audit; do not tune models to them.",
        ],
    }
    report["analysis_id"] = hashlib.sha256(encode(report)).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = analyze(args.bundle.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = encode(report)
    args.output.write_bytes(gzip.compress(data, mtime=0) if args.output.suffix == ".gz" else data)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "snapshot_id",
                    "analysis_id",
                    "calendar_days",
                    "observed_days",
                    "missing_days",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
