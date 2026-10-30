"""Screen downloaded PDFs before measurement extraction.

This identifies known placeholders, read failures, and report candidates.
A report candidate is NOT a validated analytical record.
Original PDFs and the collection journal remain unchanged.
"""

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "bpdb"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "processed" / "source_screening"

PLACEHOLDER_PHRASES = (
    "no pdf found",
    "a simple pdf file",
    "virtual mechanics tutorials",
)

REPORT_MARKERS = (
    "system summary report",
    "daily electricity generation report",
    "maximum load served",
    "evening peak generation",
    "national load dispatch",
    "national load despatch",
    "bangladesh power development board",
    "power grid",
)


def screen_source(row):
    metadata = json.loads(row["metadata"])
    result = {
        "url": row["url"],
        "category": metadata.get("category", "unknown"),
        "archive_date_hint": metadata.get("archive_date_hint"),
        "sha256": row["sha256"],
        "path": row["path"],
        "status": None,
    }

    if row["path"] is None:
        result["status"] = "unresolved_download"
        return result

    path = RAW_ROOT / row["path"]

    if not path.is_file():
        result["status"] = "missing_local_file"
        return result

    try:
        reader = PdfReader(path)
        result["page_count"] = len(reader.pages)

        # Inspect the first two pages for source identity.
        texts = []
        for index in range(min(2, len(reader.pages))):
            texts.append(reader.pages[index].extract_text() or "")

        text = "\n".join(texts)
        normalized = " ".join(text.lower().split())
        result["text_preview"] = text[:1200]
        result["screened_pages"] = len(texts)

        placeholder = next(
            (
                phrase
                for phrase in PLACEHOLDER_PHRASES
                if phrase in normalized
            ),
            None,
        )

        if placeholder:
            result["status"] = "placeholder_or_demo"
            result["matched_phrase"] = placeholder
        elif not normalized:
            result["status"] = "needs_ocr_or_review"
        elif any(marker in normalized for marker in REPORT_MARKERS):
            result["status"] = "report_candidate"
        else:
            result["status"] = "unrecognized_needs_review"

    except Exception as exc:
        result["status"] = "pdf_read_failed"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)

    return result


def main():
    journal = RAW_ROOT / "collection.sqlite3"
    if not journal.is_file():
        raise FileNotFoundError(f"Journal not found: {journal}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        journal.resolve().as_uri() + "?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            """
            SELECT s.url, s.metadata, r.sha256, r.path
            FROM sources AS s
            LEFT JOIN revisions AS r
                ON r.id = (
                    SELECT MAX(r2.id)
                    FROM revisions AS r2
                    WHERE r2.url = s.url
                )
            ORDER BY s.url
            """
        ).fetchall()
    finally:
        connection.close()

    counts = Counter()
    by_category = {}
    issues = []

    manifest_path = OUTPUT_ROOT / "screening_manifest.jsonl"
    temporary_path = OUTPUT_ROOT / "screening_manifest.jsonl.part"

    with temporary_path.open("w", encoding="utf-8") as handle:
        for index, row in enumerate(rows, 1):
            result = screen_source(row)
            status = result["status"]
            category = result["category"]

            counts[status] += 1
            category_counts = by_category.setdefault(category, Counter())
            category_counts[status] += 1

            handle.write(
                json.dumps(result, ensure_ascii=False) + "\n"
            )

            if status != "report_candidate":
                issues.append(result)

            if index % 100 == 0 or index == len(rows):
                handle.flush()
                print(
                    f"Screened {index}/{len(rows)} sources",
                    flush=True,
                )

    temporary_path.replace(manifest_path)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(rows),
        "status_counts": dict(counts),
        "by_category": {
            category: dict(values)
            for category, values in by_category.items()
        },
        "limitations": [
            "Only the latest saved revision of each URL was screened.",
            "Only the first two pages were inspected.",
            "Report candidates still require date, unit and value validation.",
            "Archive date hints must not become operational dates automatically.",
            "This screening does not recompute file checksums.",
        ],
    }

    (OUTPUT_ROOT / "screening_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    (OUTPUT_ROOT / "screening_issues.json").write_text(
        json.dumps(issues, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nResults: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()