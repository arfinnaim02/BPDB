"""Audit the collection journal and extract representative PDF text samples.

Does not alter original PDFs or write measurements to Neon.
Archive dates remain hints, not verified operational dates.
"""

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "bpdb"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "processed" / "collection_audit"


def main():
    journal = RAW_ROOT / "collection.sqlite3"
    if not journal.is_file():
        raise FileNotFoundError(f"Collection journal not found: {journal}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    # Read-only connection prevents accidental journal changes.
    connection = sqlite3.connect(
        journal.resolve().as_uri() + "?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            """
            SELECT
                s.url,
                s.metadata,
                r.sha256,
                r.path,
                r.size_bytes,
                r.page_count
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

    categories = {}
    sample_groups = defaultdict(list)
    unresolved = []
    missing_files = []
    size_mismatches = []
    downloaded = 0
    verified_size = 0

    for row in rows:
        metadata = json.loads(row["metadata"])
        category = metadata.get("category") or "unknown"
        hint = metadata.get("archive_date_hint")

        stats = categories.setdefault(
            category,
            {
                "discovered_urls": 0,
                "recorded_downloads": 0,
                "local_files_present": 0,
                "archive_date_hints": [],
            },
        )
        stats["discovered_urls"] += 1

        if hint:
            stats["archive_date_hints"].append(hint)

        if row["path"] is None:
            unresolved.append({
                "url": row["url"],
                "category": category,
                "archive_date_hint": hint,
                "status": "no_saved_revision",
            })
            continue

        downloaded += 1
        stats["recorded_downloads"] += 1
        path = RAW_ROOT / row["path"]

        if not path.is_file():
            missing_files.append({
                "url": row["url"],
                "path": str(path),
            })
            continue

        stats["local_files_present"] += 1
        actual_size = path.stat().st_size

        if actual_size != row["size_bytes"]:
            size_mismatches.append({
                "url": row["url"],
                "path": str(path),
                "expected_size": row["size_bytes"],
                "actual_size": actual_size,
            })
            continue

        verified_size += 1

        # Select samples from every category/year represented by date hints.
        year = str(hint)[:4] if hint else "undated"
        sample_groups[(category, year)].append({
            "url": row["url"],
            "category": category,
            "archive_date_hint": hint,
            "sha256": row["sha256"],
            "path": str(path),
        })

    for stats in categories.values():
        hints = sorted(stats.pop("archive_date_hints"))
        stats["earliest_archive_date_hint"] = hints[0] if hints else None
        stats["latest_archive_date_hint"] = hints[-1] if hints else None

    samples = []
    text_sections = []

    for (category, year), documents in sorted(sample_groups.items()):
        documents.sort(
            key=lambda item: (
                item["archive_date_hint"] or "",
                item["url"],
            )
        )

        # Earliest and latest candidate in each category/year.
        chosen = [documents[0]]
        if documents[-1]["url"] != documents[0]["url"]:
            chosen.append(documents[-1])

        for document in chosen:
            result = dict(document)
            heading = (
                f"\n{'=' * 72}\n"
                f"Category: {category} | Archive year hint: {year}\n"
                f"Archive date hint: {document['archive_date_hint']}\n"
                f"URL: {document['url']}\n"
                f"SHA256: {document['sha256']}\n"
            )

            try:
                reader = PdfReader(document["path"])
                result["page_count"] = len(reader.pages)

                page_texts = []
                for index, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    page_texts.append(
                        f"\n--- PDF PAGE {index + 1} ---\n{text}"
                    )

                extracted = "\n".join(page_texts)
                result["text_characters"] = len(extracted.strip())
                result["status"] = (
                    "text_extracted"
                    if extracted.strip() and any(
                        (page.extract_text() or "").strip()
                        for page in reader.pages
                    )
                    else "no_extractable_text"
                )
                text_sections.append(heading + extracted)
            except Exception as exc:
                result["status"] = "read_failed"
                result["error_type"] = type(exc).__name__
                result["error"] = str(exc)
                text_sections.append(
                    heading + f"\nREAD FAILED: {type(exc).__name__}: {exc}\n"
                )

            samples.append(result)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "discovered_urls": len(rows),
        "urls_with_saved_revision": downloaded,
        "files_present_with_matching_size": verified_size,
        "unresolved_source_count": len(unresolved),
        "missing_local_file_count": len(missing_files),
        "size_mismatch_count": len(size_mismatches),
        "categories": categories,
        "sample_count": len(samples),
        "sample_read_failures": sum(
            item["status"] == "read_failed" for item in samples
        ),
        "samples_without_text": sum(
            item["status"] == "no_extractable_text" for item in samples
        ),
        "limitations": [
            "Archive dates are hints, not verified operational dates.",
            "File sizes are checked; checksums are not recomputed here.",
            "Only representative samples are opened for text extraction.",
            "Matching size does not establish PDF validity or data accuracy.",
        ],
    }

    outputs = {
        "collection_audit.json": summary,
        "unresolved_sources.json": unresolved,
        "local_file_issues.json": {
            "missing_files": missing_files,
            "size_mismatches": size_mismatches,
        },
        "sample_manifest.json": samples,
    }

    for filename, payload in outputs.items():
        (OUTPUT_ROOT / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    (OUTPUT_ROOT / "representative_pdf_text.txt").write_text(
        "\n".join(text_sections),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nAudit output: {OUTPUT_ROOT}")

    return 1 if missing_files or size_mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())