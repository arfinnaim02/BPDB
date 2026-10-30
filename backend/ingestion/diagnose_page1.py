"""Prepare representative parser failures and same-date comparisons."""

import json
from collections import defaultdict
from pathlib import Path

import pdfplumber

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXTRACTION_ROOT = PROJECT_ROOT / "data" / "processed" / "page1_extraction"
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "bpdb"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "processed" / "parser_diagnostics"


def main():
    # Select the most recently completed full batch.
    summaries = []

    for path in EXTRACTION_ROOT.glob("*/batch_summary.json"):
        summary = json.loads(path.read_text(encoding="utf-8"))

        if not summary.get("limited_run", True):
            summaries.append((summary["created_at"], path, summary))

    if not summaries:
        raise RuntimeError("No completed full-batch summary found")

    _, summary_path, summary = max(summaries, key=lambda item: item[0])
    batch_root = summary_path.parent

    groups = defaultdict(list)
    by_date = defaultdict(list)

    for path in sorted((batch_root / "records").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))

        if record["batch_status"] != "extracted":
            extraction = record.get("extraction", {})
            parser_issues = extraction.get("issues", [])

            # Group by the actual combination of parser errors.
            signature = json.dumps(
                {
                    "status": record["batch_status"],
                    "error_type": record.get("error_type"),
                    "error": record.get("error"),
                    "issues": parser_issues,
                },
                sort_keys=True,
            )
            groups[signature].append(record)

        elif record.get("extraction"):
            date = record["extraction"]["operational_date"]
            by_date[date].append(record)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    text_path = OUTPUT_ROOT / "problem_layouts.txt"

    with text_path.open("w", encoding="utf-8") as handle:
        handle.write(
            f"Parser signature: {summary['parser_signature']}\n"
            f"Distinct problem combinations: {len(groups)}\n"
            "One representative PDF per problem combination follows.\n"
        )

        for index, (signature, records) in enumerate(groups.items(), 1):
            record = records[0]
            path = RAW_ROOT / record["original_storage_path"]

            handle.write(
                "\n" + "=" * 80 + "\n"
                f"PROBLEM GROUP {index}\n"
                f"Sources in this group: {len(records)}\n"
                f"URL: {record['source_url']}\n"
                f"SHA256: {record['source_sha256']}\n"
                f"Archive date hint: {record.get('archive_date_hint')}\n"
                f"Problem: {signature}\n"
                "--- FIRST PAGE WITH LAYOUT ---\n"
            )

            try:
                with pdfplumber.open(path) as pdf:
                    text = pdf.pages[0].extract_text(layout=True) or ""
                handle.write(text + "\n")
            except Exception as exc:
                handle.write(
                    f"READ ERROR: {type(exc).__name__}: {exc}\n"
                )

            print(
                f"Diagnostic group {index}/{len(groups)} prepared",
                flush=True,
            )

    comparisons = []

    for operational_date, records in sorted(by_date.items()):
        if len(records) < 2:
            continue

        measurement_sets = []

        for record in records:
            observations = record["extraction"]["observations"]

            # Compare parsed measurements, not formatting differences.
            measurements = sorted(
                (
                    observation["metric"],
                    observation["unit"],
                    observation["value"],
                )
                for observation in observations
            )
            measurement_sets.append(measurements)

        same_pdf = len({
            record["source_sha256"]
            for record in records
        }) == 1

        same_measurements = all(
            values == measurement_sets[0]
            for values in measurement_sets[1:]
        )

        comparisons.append({
            "operational_date": operational_date,
            "identical_pdf_checksums": same_pdf,
            "identical_parsed_measurements": same_measurements,
            "review_status": "needs_review",
            "sources": [
                {
                    "url": record["source_url"],
                    "sha256": record["source_sha256"],
                    "archive_date_hint": record.get("archive_date_hint"),
                    "reporting_date": record["extraction"].get(
                        "reporting_date"
                    ),
                    "observations": record["extraction"]["observations"],
                }
                for record in records
            ],
        })

    comparison_path = OUTPUT_ROOT / "same_date_comparisons.json"
    comparison_path.write_text(
        json.dumps(comparisons, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nProblem groups: {len(groups)}")
    print(f"Dates requiring source comparison: {len(comparisons)}")
    print(f"\nPrepared: {text_path}")
    print(f"Prepared: {comparison_path}")


if __name__ == "__main__":
    main()