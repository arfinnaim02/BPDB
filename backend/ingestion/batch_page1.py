"""Historical Page 1 extraction assessment. Does not write to Neon."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

from ingestion import page1_parser

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "bpdb"
SCREENING_ROOT = PROJECT_ROOT / "data" / "processed" / "source_screening"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "processed" / "page1_extraction"


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit must be zero or positive")

    manifest = SCREENING_ROOT / "screening_manifest.jsonl"
    with manifest.open(encoding="utf-8") as handle:
        sources = [
            record
            for line in handle
            if line.strip()
            for record in [json.loads(line)]
            if record["category"] == "page_1"
            and record["status"] == "report_candidate"
        ]

    sources.sort(key=lambda source: source["url"])
    selected = sources[:args.limit] if args.limit else sources

    # Parser changes automatically create a separate extraction directory.
    signature = (
        Path(page1_parser.__file__).read_bytes()
        + str(pdfplumber.__version__).encode()
    )
    parser_signature = hashlib.sha256(signature).hexdigest()
    output = OUTPUT_ROOT / parser_signature
    output.mkdir(parents=True, exist_ok=True)

    counts = Counter()
    layouts = Counter()
    years = Counter()
    issues = []
    dates = {}
    reused = 0

    for index, source in enumerate(selected, 1):
        identity = source["url"] + "|" + source["sha256"]
        record_id = hashlib.sha256(identity.encode()).hexdigest()
        destination = output / "records" / f"{record_id}.json"
        result = None

        if destination.is_file():
            previous = json.loads(
                destination.read_text(encoding="utf-8")
            )
            retry = (
                args.retry_failed
                and previous["batch_status"] != "extracted"
            )
            if not retry:
                result = previous
                reused += 1

        if result is None:
            result = {
                "source_url": source["url"],
                "source_sha256": source["sha256"],
                "original_storage_path": source["path"],
                "archive_date_hint": source.get("archive_date_hint"),
                "parser_signature": parser_signature,
            }

            try:
                path = RAW_ROOT / source["path"]
                digest = hashlib.sha256(path.read_bytes()).hexdigest()

                if digest != source["sha256"]:
                    raise ValueError("Original PDF checksum mismatch")

                extraction = page1_parser.parse_page1(path)
                result["extraction"] = extraction
                result["batch_status"] = (
                    "quarantined"
                    if extraction["issues"]
                    else "extracted"
                )
            except Exception as exc:
                result["batch_status"] = "failed"
                result["error_type"] = type(exc).__name__
                result["error"] = str(exc)

            write_json(destination, result)

        status = result["batch_status"]
        counts[status] += 1

        extraction = result.get("extraction")
        if extraction:
            layouts[extraction["parser_version"]] += 1
            operational_date = extraction["operational_date"]
            years[operational_date[:4]] += 1

            if status == "extracted":
                dates.setdefault(operational_date, []).append(
                    source["url"]
                )

        if status != "extracted":
            issues.append({
                "source_url": source["url"],
                "archive_date_hint": source.get("archive_date_hint"),
                "status": status,
                "error_type": result.get("error_type"),
                "error": result.get("error"),
                "parser_issues": (
                    extraction["issues"] if extraction else []
                ),
            })

        if index % 50 == 0 or index == len(selected):
            print(
                f"Processed {index}/{len(selected)} | "
                f"extracted={counts['extracted']} | "
                f"quarantined={counts['quarantined']} | "
                f"failed={counts['failed']} | reused={reused}",
                flush=True,
            )

    multiple_sources = {
        day: urls
        for day, urls in dates.items()
        if len(urls) > 1
    }

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "parser_signature": parser_signature,
        "known_page1_candidates": len(sources),
        "selected_sources": len(selected),
        "limited_run": len(selected) < len(sources),
        "reused_extractions": reused,
        "status_counts": dict(counts),
        "layouts": dict(layouts),
        "operational_years": dict(sorted(years.items())),
        "distinct_extracted_operational_dates": len(dates),
        "dates_with_multiple_sources": len(multiple_sources),
        "limitations": [
            "Extraction assessment, not final measurement validation.",
            "Only the supported Page 1 national metrics are extracted.",
            "No canonical records or measurements written to Neon.",
            "Multiple sources for a date require revision/conflict review.",
        ],
    }

    write_json(output / "batch_summary.json", summary)
    write_json(output / "batch_issues.json", issues)
    write_json(output / "multiple_sources.json", multiple_sources)

    print(json.dumps(summary, indent=2))
    print(f"\nResults folder: {output}")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())