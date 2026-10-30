"""Validate extracted Page 1 records before Neon ingestion."""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXTRACTION_ROOT = PROJECT_ROOT / "data" / "processed" / "page1_extraction"


def write_json(path, payload):
    temporary = path.with_suffix(".json.part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def check_record(record):
    extraction = record["extraction"]
    observations = extraction["observations"]
    issues = []
    values = {}
    units = {}

    for observation in observations:
        metric = observation["metric"]

        if metric in values:
            issues.append({
                "code": "duplicate_metric",
                "metric": metric,
            })
            continue

        value = Decimal(observation["value"])

        if not value.is_finite():
            issues.append({
                "code": "non_finite_value",
                "metric": metric,
            })
            continue

        values[metric] = value
        units[metric] = observation["unit"]

        if metric != "maximum_temperature" and value < 0:
            issues.append({
                "code": "negative_measurement",
                "metric": metric,
                "value": str(value),
            })

    day = datetime.strptime(
        extraction["operational_date"], "%Y-%m-%d"
    ).date()
    today_dhaka = datetime.now(
        timezone(timedelta(hours=6))
    ).date()

    if day > today_dhaka:
        issues.append({"code": "future_operational_date"})

    for metric in (
        "day_peak_generation",
        "evening_peak_generation",
        "maximum_generation",
        "energy_generated",
    ):
        if metric not in values:
            issues.append({
                "code": "missing_core_measurement",
                "metric": metric,
            })
        elif values[metric] <= 0:
            issues.append({
                "code": "non_positive_core_measurement",
                "metric": metric,
            })

    maximum = values.get("maximum_generation")

    if maximum is not None:
        for metric in (
            "day_peak_generation",
            "evening_peak_generation",
            "minimum_generation",
        ):
            if metric in values and values[metric] > maximum + Decimal("1"):
                issues.append({
                    "code": "generation_exceeds_daily_maximum",
                    "metric": metric,
                })

    if all(metric in values for metric in (
        "evening_peak_generation", "evening_peak_demand"
    )):
        if (
            values["evening_peak_generation"] > 0
            and values["evening_peak_demand"] == 0
        ):
            issues.append({
                "code": "zero_demand_with_positive_generation"
            })

    energy = values.get("energy_generated")

    if (
        energy is not None
        and maximum is not None
        and units.get("energy_generated") == "million_kWh"
        and units.get("maximum_generation") == "MW"
    ):
        # MW * 24 hours / 1000 = million kWh.
        ceiling = maximum * Decimal("24") / Decimal("1000")
        tolerance = max(Decimal("0.1"), ceiling * Decimal("0.001"))

        if energy > ceiling + tolerance:
            issues.append({
                "code": "energy_exceeds_peak_based_daily_ceiling",
                "energy_million_kWh": str(energy),
                "ceiling_million_kWh": str(ceiling),
            })

    cost = values.get("total_production_cost")
    rate = values.get("production_cost_per_kwh")

    if (
        cost is not None
        and rate is not None
        and energy is not None
        and energy > 0
        and units.get("energy_generated") == "million_kWh"
        and units.get("total_production_cost") == "BDT"
        and units.get("production_cost_per_kwh") == "BDT/kWh"
    ):
        implied_cost = energy * Decimal("1000000") * rate
        relative_difference = (
            abs(cost - implied_cost)
            / max(abs(cost), Decimal("1"))
        )

        # Review flag only; do not replace any source value.
        if relative_difference > Decimal("0.005"):
            issues.append({
                "code": "cost_rate_requires_review",
                "reported_cost": str(cost),
                "energy_times_rate": str(implied_cost),
                "relative_difference": str(relative_difference),
            })

    return issues


def observation_signature(record):
    return tuple(sorted(
        (
            observation["metric"],
            observation["unit"],
            Decimal(observation["value"]),
        )
        for observation in record["extraction"]["observations"]
    ))


def main():
    candidates = []

    for path in EXTRACTION_ROOT.glob("*/batch_summary.json"):
        summary = json.loads(path.read_text(encoding="utf-8"))
        if not summary.get("limited_run", True):
            candidates.append((summary["created_at"], path))

    if not candidates:
        raise RuntimeError("No full-batch extraction summary found")

    _, summary_path = max(candidates, key=lambda item: item[0])
    batch_root = summary_path.parent
    output = batch_root / "validation"
    output.mkdir(parents=True, exist_ok=True)

    counts = Counter()
    issues_output = []
    valid_by_date = defaultdict(list)

    for path in sorted((batch_root / "records").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))

        if record["batch_status"] != "extracted":
            counts["excluded_parser_issue"] += 1
            continue

        counts["assessed_extracted_sources"] += 1

        try:
            issues = check_record(record)
        except Exception as exc:
            issues = [{
                "code": "validation_exception",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }]

        if issues:
            counts["sources_requiring_review"] += 1
            issues_output.append({
                "source_url": record["source_url"],
                "sha256": record["source_sha256"],
                "operational_date": record["extraction"]["operational_date"],
                "issues": issues,
            })
            continue

        counts["sources_passing_current_checks"] += 1
        day = record["extraction"]["operational_date"]
        valid_by_date[day].append({
            "record": record,
            "record_path": str(path.relative_to(batch_root)),
        })

    groups = []
    eligibility = Counter()

    for day, entries in sorted(valid_by_date.items()):
        records = [entry["record"] for entry in entries]
        same_pdf = len({
            record["source_sha256"] for record in records
        }) == 1
        signatures = [
            observation_signature(record) for record in records
        ]
        same_values = all(
            signature == signatures[0]
            for signature in signatures[1:]
        )

        if len(records) == 1:
            classification = "single_source"
        elif same_pdf:
            classification = "identical_pdf_sources"
        elif same_values:
            classification = "different_pdfs_matching_current_metrics"
        else:
            classification = "measurement_conflict"

        eligibility[classification] += 1

        groups.append({
            "operational_date": day,
            "classification": classification,
            "sources": [
                {
                    "url": entry["record"]["source_url"],
                    "sha256": entry["record"]["source_sha256"],
                    "record_path": entry["record_path"],
                }
                for entry in entries
            ],
        })

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "batch_folder": batch_root.name,
        "counts": dict(counts),
        "date_group_counts": dict(eligibility),
        "dates_passing_current_checks": len(valid_by_date),
        "limitations": [
            "Passing these checks does not establish full source accuracy.",
            "Different PDF revisions require review before canonical selection.",
            "Missing dates and field completeness require a separate coverage audit.",
            "No source values were corrected or imputed.",
            "No records were written to Neon.",
        ],
    }

    write_json(output / "validation_summary.json", summary)
    write_json(output / "validation_issues.json", issues_output)
    write_json(output / "date_groups.json", groups)

    print(json.dumps(summary, indent=2))
    print(f"\nResults: {output}")


if __name__ == "__main__":
    main()