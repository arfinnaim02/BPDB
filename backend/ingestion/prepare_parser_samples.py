"""Copy representative original PDFs for parser development."""

import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "bpdb"
SCREENING_ROOT = PROJECT_ROOT / "data" / "processed" / "source_screening"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "samples" / "parser_development"


def main():
    manifest = SCREENING_ROOT / "screening_manifest.jsonl"
    if not manifest.is_file():
        raise FileNotFoundError(f"Screening manifest not found: {manifest}")

    with manifest.open(encoding="utf-8") as handle:
        records = [
            json.loads(line)
            for line in handle
            if line.strip()
        ]

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    selected = []

    for category in ("page_1", "summary"):
        candidates = [
            record
            for record in records
            if record["category"] == category
            and record["status"] == "report_candidate"
            and record.get("archive_date_hint")
            and record.get("path")
        ]

        if not candidates:
            raise RuntimeError(f"No dated candidates found for {category}")

        # Hints select a spread of samples, not operational dates.
        candidates.sort(
            key=lambda record: (
                record["archive_date_hint"],
                record["url"],
            )
        )

        for label, record in (
            ("older", candidates[0]),
            ("recent", candidates[-1]),
        ):
            filename = f"{category}_{label}.pdf"
            source = RAW_ROOT / record["path"]
            destination = OUTPUT_ROOT / filename

            shutil.copyfile(source, destination)

            selected.append({
                "sample_filename": filename,
                "original_url": record["url"],
                "sha256": record["sha256"],
                "archive_date_hint": record["archive_date_hint"],
                "original_storage_path": record["path"],
            })

            print(f"Prepared: {destination}")

    (OUTPUT_ROOT / "sample_sources.json").write_text(
        json.dumps(selected, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nSample folder: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()