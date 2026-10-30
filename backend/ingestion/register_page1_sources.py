"""Register eligible original Page 1 PDFs in Neon.

Default: local preview.
--apply: register source metadata using existing foundation tables.
Does not insert measurements or promote canonical daily records.
"""

import argparse
import hashlib
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from app.db.models import IngestionRun, SourceDocument
from app.db.session import session_factory
from sqlalchemy.dialects.postgresql import insert

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "bpdb"
EXTRACTION_ROOT = PROJECT_ROOT / "data" / "processed" / "page1_extraction"

DEFAULT_BATCH = (
    "a50e4962dea59c8d517795697cc9f4484cafc7089d6c0c6de99930a81af5bf33"
)


def prepare_sources(batch_root):
    validation_root = batch_root / "validation"
    summary = json.loads(
        (validation_root / "validation_summary.json").read_text(
            encoding="utf-8"
        )
    )
    groups = json.loads(
        (validation_root / "date_groups.json").read_text(
            encoding="utf-8"
        )
    )

    if summary["batch_folder"] != batch_root.name:
        raise ValueError("Validation summary belongs to another batch")

    eligible = [
        group
        for group in groups
        if group["classification"] in (
            "single_source",
            "identical_pdf_sources",
        )
    ]

    journal_path = RAW_ROOT / "collection.sqlite3"
    connection = sqlite3.connect(
        journal_path.resolve().as_uri() + "?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    prepared = []
    seen = set()

    try:
        for group in eligible:
            for source in group["sources"]:
                record_path = (
                    batch_root
                    / source["record_path"].replace("\\", "/")
                )
                record = json.loads(
                    record_path.read_text(encoding="utf-8")
                )

                if record["batch_status"] != "extracted":
                    raise ValueError("Selected record is not extracted")

                if (
                    record["source_url"] != source["url"]
                    or record["source_sha256"] != source["sha256"]
                    or record["extraction"]["operational_date"]
                    != group["operational_date"]
                    or record["extraction"]["issues"]
                ):
                    raise ValueError("Validation/source reference mismatch")

                key = (source["url"], source["sha256"])
                if key in seen:
                    continue
                seen.add(key)

                revision = connection.execute(
                    """
                    SELECT r.*, s.metadata
                    FROM revisions AS r
                    JOIN sources AS s ON s.url = r.url
                    WHERE r.url = ? AND r.sha256 = ?
                    """,
                    key,
                ).fetchone()

                if revision is None:
                    raise ValueError("Source revision missing from journal")

                path = RAW_ROOT / revision["path"]
                data = path.read_bytes()

                if hashlib.sha256(data).hexdigest() != source["sha256"]:
                    raise ValueError(f"Checksum mismatch: {path}")

                if len(data) != revision["size_bytes"]:
                    raise ValueError(f"File size mismatch: {path}")

                metadata = json.loads(revision["metadata"])
                if metadata.get("category") != "page_1":
                    raise ValueError("Unexpected source category")

                hint = metadata.get("archive_date_hint")
                retrieved_at = datetime.fromisoformat(
                    revision["retrieved_at"]
                )
                if retrieved_at.tzinfo is None:
                    raise ValueError("Retrieval timestamp lacks timezone")

                prepared.append({
                    "original_url": source["url"],
                    "category": "page_1",
                    "sha256": source["sha256"],
                    "storage_key": revision["path"],
                    "original_filename": unquote(
                        Path(urlsplit(source["url"]).path).name
                    ),
                    "content_type": revision["content_type"]
                    or "application/pdf",
                    "size_bytes": revision["size_bytes"],
                    # Preserve archive hints separately.
                    # Operational dates will be assigned during
                    # reviewed extraction ingestion.
                    "report_date": None,
                    "archive_date_hint": (
                        date.fromisoformat(hint) if hint else None
                    ),
                    "published_at": None,
                    "retrieved_at": retrieved_at,
                    "parser_version": None,
                    "status": "downloaded",
                })
    finally:
        connection.close()

    return eligible, prepared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    batch_root = EXTRACTION_ROOT / args.batch
    groups, prepared = prepare_sources(batch_root)

    print(f"Eligible date groups: {len(groups)}")
    print(f"Verified original sources: {len(prepared)}")

    if not args.apply:
        print("Preview complete. No Neon changes made.")
        return 0

    if not prepared:
        raise ValueError("No eligible sources to register")

    factory = session_factory()
    run_id = str(uuid4())
    inserted = 0
    skipped = 0

    with factory.begin() as session:
        session.add(IngestionRun(
            id=run_id,
            trigger="manual",
            status="running",
            statistics={
                "stage": "page1_source_registration",
                "batch": args.batch,
            },
        ))

    try:
        for offset in range(0, len(prepared), 100):
            chunk = prepared[offset:offset + 100]
            rows = [
                {
                    **source,
                    "id": str(uuid4()),
                    "created_at": datetime.now(timezone.utc),
                    "ingestion_run_id": run_id,
                }
                for source in chunk
            ]

            statement = (
                insert(SourceDocument)
                .values(rows)
                .on_conflict_do_nothing(
                    index_elements=["original_url", "sha256"]
                )
                .returning(SourceDocument.id)
            )

            with factory.begin() as session:
                new_ids = session.execute(statement).scalars().all()

            inserted += len(new_ids)
            skipped += len(chunk) - len(new_ids)

            print(
                f"Registered {offset + len(chunk)}/{len(prepared)} | "
                f"inserted={inserted} | existing={skipped}",
                flush=True,
            )

        with factory.begin() as session:
            run = session.get(IngestionRun, run_id)
            run.status = "succeeded"
            run.finished_at = datetime.now(timezone.utc)
            run.statistics = {
                "stage": "page1_source_registration",
                "batch": args.batch,
                "inserted": inserted,
                "existing": skipped,
                "eligible_date_groups": len(groups),
            }

    except Exception as exc:
        with factory.begin() as session:
            run = session.get(IngestionRun, run_id)
            run.status = "partial" if inserted else "failed"
            run.finished_at = datetime.now(timezone.utc)
            run.error_code = type(exc).__name__
            run.statistics = {
                "stage": "page1_source_registration",
                "inserted": inserted,
                "existing": skipped,
            }

        print(
            f"Registration stopped: {type(exc).__name__}. "
            "Committed sources remain saved; rerunning is safe."
        )
        return 1

    print(json.dumps({
        "status": "succeeded",
        "run_id": run_id,
        "inserted": inserted,
        "existing": skipped,
        "measurements_inserted": 0,
        "canonical_records_promoted": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())