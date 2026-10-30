"""Incremental Page 1 ingestion using the existing collector and Neon schema."""

import argparse
import hashlib
import inspect
import json
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from app.db.models import (
    DailyReport,
    ExtractionIssue,
    IngestionRun,
    ReportVersion,
    SourceDocument,
    VersionSource,
)
from app.db.session import session_factory
from app.services.canonical import promote_version
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from ingestion import page1_parser, validate_page1
from ingestion.collect_pdfs import download_pdf, open_journal, scan_archive
from ingestion.http import create_client
from ingestion.import_page1_measurements import METRICS, import_group

ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / "data" / "raw" / "bpdb"


def utcnow():
    return datetime.now(timezone.utc)


def recent_documents(db, lookback_days):
    today = datetime.now(timezone(timedelta(hours=6))).date()
    cutoff = today - timedelta(days=lookback_days - 1)
    selected = []

    for row in db.execute("SELECT metadata FROM sources ORDER BY url"):
        document = json.loads(row[0])

        try:
            hint = date.fromisoformat(
                document.get("archive_date_hint") or ""
            )
        except ValueError:
            continue

        if hint >= cutoff:
            selected.append(document)

    return selected


def numeric_issues(extraction):
    issues = []
    seen = set()

    for observation in extraction["observations"]:
        metric = observation["metric"]

        if metric not in METRICS or metric in seen:
            issues.append({
                "code": "unknown_or_duplicate_metric",
                "metric": metric,
            })
            continue

        seen.add(metric)

        if observation["unit"] != METRICS[metric][1]:
            issues.append({
                "code": "unexpected_unit",
                "metric": metric,
            })

        value = Decimal(observation["value"])

        if not value.is_finite() or abs(value) >= Decimal("1e18"):
            issues.append({
                "code": "invalid_numeric_value",
                "metric": metric,
            })
        elif value != value.quantize(Decimal("0.000001")):
            issues.append({
                "code": "database_precision_loss",
                "metric": metric,
            })

    return issues


@contextmanager
def collector_lock(root):
    with (root / "collector.lock").open("a+b") as handle:
        handle.seek(0)

        if not handle.read(1):
            handle.write(b"0")
            handle.flush()

        handle.seek(0)

        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

        try:
            yield
        finally:
            handle.seek(0)

            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def policy_signature():
    digest = hashlib.sha256()

    for module in (page1_parser, validate_page1):
        digest.update(Path(module.__file__).read_bytes())

    digest.update(Path(__file__).read_bytes())
    digest.update(inspect.getsource(import_group).encode())

    rules = [
        (key, item[0].__tablename__, item[1], item[2], item[3])
        for key, item in sorted(METRICS.items())
    ]
    digest.update(json.dumps(rules, sort_keys=True).encode())

    return "daily:" + digest.hexdigest()


def process_source(session, document, revision, run_id, policy):
    retrieved = datetime.fromisoformat(revision["retrieved_at"])

    if retrieved.tzinfo is None:
        raise ValueError("Retrieval timestamp lacks timezone")

    source_id = session.scalar(
        insert(SourceDocument)
        .values(
            id=str(uuid4()),
            created_at=utcnow(),
            original_url=document["url"],
            category=document["category"],
            sha256=revision["sha256"],
            storage_key=revision["path"],
            original_filename=unquote(
                Path(urlsplit(document["url"]).path).name
            ),
            content_type=revision["content_type"] or "application/pdf",
            size_bytes=revision["size_bytes"],
            report_date=None,
            archive_date_hint=date.fromisoformat(
                document["archive_date_hint"]
            ),
            published_at=None,
            retrieved_at=retrieved,
            parser_version=None,
            status="downloaded",
            ingestion_run_id=run_id,
        )
        .on_conflict_do_nothing(
            index_elements=["original_url", "sha256"]
        )
        .returning(SourceDocument.id)
    )

    if source_id is None:
        source_id = session.scalar(
            select(SourceDocument.id).where(
                SourceDocument.original_url == document["url"],
                SourceDocument.sha256 == revision["sha256"],
            )
        )

    source = session.get(SourceDocument, source_id)

    if document["category"] != "page_1":
        return "raw_only"

    linked = session.scalar(
        select(VersionSource.version_id)
        .where(VersionSource.source_id == source_id)
        .limit(1)
    )

    if linked:
        return "already_linked"

    if (
        source.parser_version == policy
        and source.status == "quarantined"
    ):
        return "held_quarantine"

    source.parser_version = policy
    path = RAW_ROOT / revision["path"]
    issues = []
    extraction = None

    try:
        extraction = page1_parser.parse_page1(path)
        issues.extend(extraction["issues"])
        issues.extend(
            validate_page1.check_record({"extraction": extraction})
        )
        issues.extend(numeric_issues(extraction))
    except Exception as exc:
        issues.append({
            "code": "extraction_failed",
            "error_type": type(exc).__name__,
        })

    if issues:
        source.status = "quarantined"
        session.add(ExtractionIssue(
            source_id=source_id,
            code="daily_validation_failed",
            severity="error",
            details={"policy": policy, "issues": issues},
        ))
        return "quarantined"

    record = {
        "source_url": document["url"],
        "source_sha256": revision["sha256"],
        "extraction": extraction,
    }
    group = {
        "operational_date": extraction["operational_date"]
    }
    version_key = "daily:" + hashlib.sha256(
        (policy + revision["sha256"] + document["url"]).encode()
    ).hexdigest()

    session.info["registered_source_ids"] = {
        (document["url"], revision["sha256"]): source_id
    }

    import_group(session, group, [record], version_key)

    report = session.scalar(
        select(DailyReport)
        .where(
            DailyReport.report_date == date.fromisoformat(
                group["operational_date"]
            ),
            DailyReport.dataset_grain == "national_daily",
        )
        .with_for_update()
    )

    version = session.scalar(
        select(ReportVersion).where(
            ReportVersion.report_id == report.id,
            ReportVersion.parser_version == version_key,
        )
    )

    other_version = session.scalar(
        select(ReportVersion.id)
        .where(
            ReportVersion.report_id == report.id,
            ReportVersion.id != version.id,
        )
        .limit(1)
    )

    if report.current_version_id is None and other_version is None:
        version.quality_status = "validated"
        session.flush()

        promote_version(session, report.id, version.id)
        source.status = "processed"
        return "promoted"

    version.quality_status = "conflict"
    source.status = "review_required"

    session.add(ExtractionIssue(
        source_id=source_id,
        version_id=version.id,
        code="daily_canonical_review",
        severity="warning",
        details={
            "operational_date": group["operational_date"],
            "existing_canonical_version": report.current_version_id,
        },
    ))

    return "review_required"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--trigger",
        choices=("manual", "scheduled"),
        default="manual",
    )
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--max-pages", type=int, default=6)
    parser.add_argument("--max-documents", type=int, default=200)
    args = parser.parse_args()

    if (
        not 1 <= args.lookback_days <= 90
        or not 1 <= args.max_pages <= 100
    ):
        parser.error("Use lookback-days 1..90 and max-pages 1..100")

    if args.max_documents < 1:
        parser.error("max-documents must be positive")

    if not args.apply:
        journal = RAW_ROOT / "collection.sqlite3"

        if not journal.is_file():
            print(
                "No local journal yet. "
                "First apply run will discover recent reports."
            )
            return 0

        db = sqlite3.connect(
            journal.resolve().as_uri() + "?mode=ro",
            uri=True,
        )

        try:
            documents = recent_documents(db, args.lookback_days)
        finally:
            db.close()

        print(json.dumps({
            "mode": "preview",
            "known_recent_sources": len(documents),
            "page1_sources": sum(
                document["category"] == "page_1"
                for document in documents
            ),
            "note": (
                "No live discovery, downloads or Neon writes in preview."
            ),
        }, indent=2))
        return 0

    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    factory = session_factory()

    stats = {
        key: 0
        for key in (
            "downloaded",
            "cached",
            "download_failed",
            "processing_failed",
            "raw_only",
            "already_linked",
            "held_quarantine",
            "quarantined",
            "promoted",
            "review_required",
            "export_failed",
        )
    }

    run_id = str(uuid4())
    policy = policy_signature()
    fatal = None

    with collector_lock(RAW_ROOT):
        with factory.begin() as session:
            session.add(IngestionRun(
                id=run_id,
                trigger=args.trigger,
                status="running",
                statistics={
                    "stage": "daily_worker",
                    "policy": policy,
                },
            ))

        db = open_journal(RAW_ROOT)

        try:
            with create_client() as client:
                print(
                    "Discovering recent archive pages...",
                    flush=True,
                )
                scan = scan_archive(
                    client,
                    db,
                    RAW_ROOT,
                    args.max_pages,
                    1.0,
                    daily=True,
                )
                stats["archive_scan"] = scan

                documents = recent_documents(
                    db, args.lookback_days
                )

                if len(documents) > args.max_documents:
                    raise ValueError(
                        "Recent source count exceeds max-documents; "
                        "review before increasing"
                    )

                if not documents:
                    raise ValueError(
                        "No dated recent sources found; "
                        "inspect archive and date hints"
                    )

                print(
                    f"Checking {len(documents)} recent PDF sources...",
                    flush=True,
                )

                for index, document in enumerate(documents, 1):
                    try:
                        status = download_pdf(
                            client,
                            db,
                            RAW_ROOT,
                            document,
                            False,
                        )
                        stats[status] += 1
                    except Exception as exc:
                        stats["download_failed"] += 1
                        print(
                            f"PDF {index}/{len(documents)}: "
                            f"download failed ({type(exc).__name__})",
                            flush=True,
                        )
                        time.sleep(1)
                        continue

                    revision = db.execute(
                        "SELECT * FROM revisions WHERE url=? "
                        "ORDER BY id DESC LIMIT 1",
                        (document["url"],),
                    ).fetchone()

                    try:
                        with factory.begin() as session:
                            session.execute(text(
                                "SET LOCAL statement_timeout = '60000'"
                            ))
                            status = process_source(
                                session,
                                document,
                                revision,
                                run_id,
                                policy,
                            )

                        stats[status] += 1
                        print(
                            f"PDF {index}/{len(documents)}: {status}",
                            flush=True,
                        )
                    except Exception as exc:
                        stats["processing_failed"] += 1
                        print(
                            f"PDF {index}/{len(documents)}: "
                            f"processing failed ({type(exc).__name__})",
                            flush=True,
                        )

                    time.sleep(1)

            if stats["promoted"]:
                print(
                    "Exporting updated canonical data from Neon...",
                    flush=True,
                )
                exported = subprocess.run(
                    [
                        sys.executable,
                        "-u",
                        "-m",
                        "ingestion.export_master",
                    ],
                    cwd=ROOT,
                    check=False,
                )
                stats["export_failed"] = int(
                    exported.returncode != 0
                )

        except (Exception, KeyboardInterrupt) as exc:
            fatal = type(exc).__name__
        finally:
            db.close()

        scan = stats.get("archive_scan", {})
        partial = bool(
            fatal
            or stats["download_failed"]
            or stats["processing_failed"]
            or stats["quarantined"]
            or stats["review_required"]
            or stats["export_failed"]
            or scan.get("page_failures")
            or scan.get("safety_cap_reached")
        )
        status = "partial" if partial else "succeeded"

        with factory.begin() as session:
            run = session.get(IngestionRun, run_id)
            run.status = status
            run.finished_at = utcnow()
            run.error_code = fatal
            run.statistics = {
                "stage": "daily_worker",
                "policy": policy,
                **stats,
            }

        print(json.dumps({
            "run_id": run_id,
            "status": status,
            "error_type": fatal,
            **stats,
        }, indent=2), flush=True)

    return 1 if partial else 0


if __name__ == "__main__":
    raise SystemExit(main())