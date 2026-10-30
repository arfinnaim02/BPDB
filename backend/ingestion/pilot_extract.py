"""Extract the two supplied Page 1 samples and verify known values."""

import hashlib
import json
from pathlib import Path

from ingestion.page1_parser import parse_page1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_ROOT = PROJECT_ROOT / "data" / "samples" / "parser_development"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "processed" / "extraction_pilot"

EXPECTED = {
    "page_1_older.pdf": {
        "date": "2019-11-30",
        "energy": "166.4",
        "count": 5,
    },
    "page_1_recent.pdf": {
        "date": "2026-10-27",
        "energy": "324.38721",
        "count": 13,
    },
}


def main():
    sources = json.loads(
        (SAMPLE_ROOT / "sample_sources.json").read_text(
            encoding="utf-8"
        )
    )
    metadata = {
        source["sample_filename"]: source
        for source in sources
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    failures = []

    for filename, expected in EXPECTED.items():
        try:
            path = SAMPLE_ROOT / filename
            source = metadata[filename]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()

            if digest != source["sha256"]:
                raise ValueError("Sample checksum does not match manifest")

            result = parse_page1(path)
            result["source_url"] = source["original_url"]
            result["sha256"] = digest
            result["sample_filename"] = filename
            result["archive_date_hint"] = source["archive_date_hint"]

            energy = next(
                observation["value"]
                for observation in result["observations"]
                if observation["metric"] == "energy_generated"
            )

            checks = {
                "operational_date_matches": (
                    result["operational_date"] == expected["date"]
                ),
                "energy_matches": energy == expected["energy"],
                "measurement_count_matches": (
                    len(result["observations"]) == expected["count"]
                ),
                "no_parser_issues": not result["issues"],
            }
            result["sample_checks"] = checks

            if not all(checks.values()):
                failures.append({
                    "sample": filename,
                    "checks": checks,
                })

            results.append(result)
            print(
                f"{filename}: "
                f"{result['operational_date']}, "
                f"{len(result['observations'])} measurements, "
                f"{'PASS' if all(checks.values()) else 'FAIL'}"
            )

        except Exception as exc:
            failures.append({
                "sample": filename,
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
            print(f"{filename}: FAILED: {exc}")

    output = {
        "status": "passed" if not failures else "failed",
        "results": results,
        "failures": failures,
        "scope": "Two-sample Page 1 extraction pilot only",
    }

    destination = OUTPUT_ROOT / "pilot_results.json"
    destination.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nResults: {destination}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())