"""Apply only the two source-reviewed January 2024 gap repairs.

Original bytes, exact extraction, registered lineage and full database readback
are mandatory. Staging and promotion use separate transactions; no replacement
of a canonical record is permitted. Availability timestamps remain unknown.
"""

import argparse
import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.db.models import DailyReport, IngestionRun, ReportVersion, SourceDocument, VersionSource
from app.db.session import session_factory
from app.services.canonical import promote_version
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from ingestion.import_page1_measurements import METRICS, TABLES, import_group
from ingestion.page1_parser import parse_page1
from ingestion.validate_page1 import check_record

ROOT = Path(__file__).resolve().parents[2]
REVIEW = (
    ("7390page1.pdf", "d137b0ba773bbb9b9c37d71607f608166cad0d8cff9c9402d232ba9f2953987d",
     "2024-01-01", "2024-01-02", ("9084", "9944", "9944", "9944", "198.094")),
    ("7396page1.pdf", "2c8d54b6ed4d1e490c7b1ec427aaf728acdff117c051ff251478bdfe12da0ed7",
     "2024-01-04", "2024-01-05", ("9508", "10107", "10107", "10107", "206.896")),
)
FIELDS = ("day_peak_generation", "evening_peak_generation", "evening_peak_demand",
          "maximum_generation", "energy_generated")
REVIEW_HASH = hashlib.sha256(json.dumps(REVIEW).encode()).hexdigest()
KEY = "reviewed:" + REVIEW_HASH
SPRING_REVIEW = (
    ("7614page1.pdf", "a42f66f0b99d97046c2597ca4057451d1fd292579a0362f335e395205e27b8d1",
     "2024-04-20", "2024-04-21", ("13325", "15358", "15750", "15358", "327.645")),
    ("7684page1.pdf", "ed683801649616264678baf8d92c185f207a5c12b1b7cf5beb58bf75fb2f4235",
     "2024-05-25", "2024-05-26", ("13726", "14623", "14900", "14707", "337.880"),
     "legacy_page1_v5"),
)


def validate_pdf(path, review):
    name, sha, day, reporting, values = review[:5]
    expected_parser = review[5] if len(review) > 5 else "legacy_page1_v4"
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise ValueError("Reviewed PDF checksum mismatch")
    extraction = parse_page1(path)
    observations = extraction["observations"]
    expected = sorted((m, METRICS[m][1], Decimal(v)) for m, v in zip(FIELDS, values, strict=True))
    actual = sorted((o["metric"], o["unit"], Decimal(o["value"])) for o in observations)
    if (extraction["operational_date"] != day or extraction["reporting_date"] != reporting
            or extraction["parser_version"] != expected_parser
            or extraction["issues"] or check_record({"extraction": extraction})
            or actual != expected
            or any(o["source_page"] != 1 or not o["raw_text"] for o in observations)):
        raise ValueError("Source no longer matches the exact reviewed extraction")
    return {"source_url": "https://misc.bpdb.gov.bd/storage/daily_archive/" + name,
            "source_sha256": sha, "extraction": extraction}


def lock_day(session, day):
    if session.bind.dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                        {"key": "bpdb:national_daily:" + day})


def inspect_stage(session, record, *, required=False, allow_unregistered=False, version_key=KEY):
    day = date.fromisoformat(record["extraction"]["operational_date"])
    report = session.scalar(select(DailyReport).where(
        DailyReport.report_date == day, DailyReport.dataset_grain == "national_daily"
    ).with_for_update())
    source = session.scalar(select(SourceDocument).where(
        SourceDocument.original_url == record["source_url"],
        SourceDocument.sha256 == record["source_sha256"]))
    versions = list(session.scalars(select(ReportVersion).where(
        ReportVersion.report_id == report.id))) if report else []
    matches = [v for v in versions if v.parser_version == version_key]
    if len(matches) > 1:
        raise ValueError("Ambiguous reviewed stage")
    version = matches[0] if matches else None
    if report and report.current_version_id and (
            version is None or report.current_version_id != version.id):
        raise ValueError("Another canonical record exists; replacement is forbidden")
    if any(v.id != (version.id if version else None)
           and v.quality_status in ("partial", "validated", "conflict") for v in versions):
        raise ValueError("Competing staged version requires separate review")
    if source is None and not (allow_unregistered and version is None):
        raise ValueError("Reviewed source must already be registered with this checksum")
    if version is None:
        if required:
            raise ValueError("Reviewed stage is missing")
        return report, None, source
    if version.quality_status not in ("partial", "validated"):
        raise ValueError("Reviewed version is not eligible")
    links = set(session.scalars(select(VersionSource.source_id).where(
        VersionSource.version_id == version.id)))
    expected = Counter()
    for o in record["extraction"]["observations"]:
        table, unit, period, dimensions = METRICS[o["metric"]]
        expected[(table.__tablename__, o["metric"], unit, Decimal(o["value"]),
                  "national", period, dimensions.get("fuel"), source.id, 1, o["raw_text"])] += 1
    actual = Counter()
    for table in TABLES:
        for row in session.scalars(select(table).where(table.version_id == version.id)):
            actual[(table.__tablename__, row.metric, row.unit, row.value, row.zone,
                    row.period, getattr(row, "fuel", None), row.source_id,
                    row.source_page, row.raw_text)] += 1
    if links != {source.id} or actual != expected or version.available_at is not None:
        raise ValueError("Staged values, dimensions, provenance or availability mismatch")
    if report.current_version_id == version.id and version.quality_status != "validated":
        raise ValueError("Canonical version is not validated")
    return report, version, source


def register_source(session, record, run_id):
    """Register only bytes revalidated against the pinned review in this process."""
    evidence = record["registration_evidence"]
    retrieved = datetime.fromisoformat(evidence["retrieved_at"])
    if retrieved.tzinfo is None or evidence["size_bytes"] <= 0:
        raise ValueError("Invalid verified retrieval metadata")
    session.execute(insert(SourceDocument).values(
        id=str(uuid4()), original_url=record["source_url"], category="page_1",
        sha256=record["source_sha256"], storage_key="drive://" + evidence["drive_file_id"],
        original_filename=record["source_url"].rsplit("/", 1)[-1],
        content_type="application/pdf", size_bytes=evidence["size_bytes"],
        report_date=date.fromisoformat(record["extraction"]["operational_date"]),
        archive_date_hint=None, published_at=None, retrieved_at=retrieved,
        parser_version=record["extraction"]["parser_version"],
        status="downloaded", ingestion_run_id=run_id,
    ).on_conflict_do_nothing(index_elements=["original_url", "sha256"]))
    session.flush()


def transact(factory, records, action, review_hash=REVIEW_HASH):
    version_key = "reviewed:" + review_hash
    result = {"stage": "reviewed_gap_recovery", "action": action,
              "review_sha256": review_hash, "inserted_measurements": 0,
              "promoted": 0, "already_canonical": 0, "verified_measurements": 0,
              "unregistered_sources": 0}
    with factory.begin() as session:
        if session.bind.dialect.name == "postgresql":
            session.execute(text("SET LOCAL statement_timeout = '60000'"))
            session.execute(text("SET LOCAL lock_timeout = '15000'"))
        run = None
        if action in ("stage", "promote"):
            run = IngestionRun(trigger="manual", status="running")
            session.add(run)
            session.flush()
        for record in records:
            lock_day(session, record["extraction"]["operational_date"])
            report, version, source = inspect_stage(
                session, record, allow_unregistered=action in ("preview", "stage"),
                version_key=version_key,
            )
            if source is None:
                result["unregistered_sources"] += 1
                if action == "stage":
                    register_source(session, record, run.id)
                    report, version, source = inspect_stage(
                        session, record, version_key=version_key
                    )
            if action == "stage" and version is None:
                session.info["registered_source_ids"] = {
                    (record["source_url"], record["source_sha256"]): source.id}
                _, count = import_group(session, {"operational_date":
                    record["extraction"]["operational_date"]}, [record], version_key)
                result["inserted_measurements"] += count
                report, version, source = inspect_stage(
                    session, record, required=True, version_key=version_key
                )
                version.correction_reason = (
                    "Source-reviewed PDF geometry recovery; review " + review_hash
                )
            if action in ("verify", "promote"):
                report, version, source = inspect_stage(
                    session, record, required=True, version_key=version_key
                )
            if version:
                result["verified_measurements"] += 5
                if report.current_version_id == version.id:
                    result["already_canonical"] += 1
                elif action == "promote":
                    version.quality_status = "validated"
                    session.flush()
                    result["promoted"] += int(promote_version(session, report.id, version.id))
        if run:
            run.status = "succeeded"
            run.finished_at = datetime.now(timezone.utc)
            run.statistics = {**result, "reviewed_sources": records}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "stage", "verify", "promote"))
    parser.add_argument("--batch", choices=("january", "spring"), default="january")
    args = parser.parse_args()
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    from ingestion.drive_sync import download, find_files, upload_blob
    from ingestion.setup_drive_storage import CONFIG_FILE, SCOPES, TOKEN_FILE

    credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    credentials.refresh(Request())
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    folder = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))["folder_id"]
    output = ROOT / "data" / "reviewed_recovery"
    output.mkdir(parents=True, exist_ok=True)
    records = []
    reviews = SPRING_REVIEW if args.batch == "spring" else REVIEW
    review_hash = hashlib.sha256(json.dumps(reviews).encode()).hexdigest()
    for review in reviews:
        blobs = find_files(service, folder, "blob", review[1])
        if not blobs:
            raise ValueError("Reviewed original PDF is not in verified Drive storage")
        target = output / review[0]
        download(service, blobs[0]["id"], target)
        record = validate_pdf(target, review)
        record["registration_evidence"] = {
            "drive_file_id": blobs[0]["id"], "size_bytes": target.stat().st_size,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "retrieval": "verified_archived_pdf_download",
            "original_publication_time": "unknown",
        }
        records.append(record)
    result = transact(session_factory(), records, args.action, review_hash)
    result["batch"] = args.batch
    result["sources"] = records
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report_path = output / (stamp + "_" + args.action + ".json")
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    receipt = upload_blob(service, folder, report_path)
    if receipt["sha256"] != hashlib.sha256(report_path.read_bytes()).hexdigest():
        raise ValueError("Recovery audit storage checksum mismatch")
    print(json.dumps({k: v for k, v in result.items() if k != "sources"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
