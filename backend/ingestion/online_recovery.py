"""Bounded hosted source investigation. No canonical imports or checkpoint replacement."""

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from app.api.monitoring import read_session
from app.api.recovery import read_worklist

from ingestion.discovery import official_url
from ingestion.validate_page1 import check_record

ROOT = Path(__file__).resolve().parents[2]
RULE_VERSION = "online_recovery_v2"
MAX_BYTES = 30 * 1024 * 1024


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def request_bytes(client, url, limit):
    from ingestion.collect_pdfs import request_bytes as fetch

    return fetch(client, url, limit)


def create_client(**kwargs):
    from ingestion.http import create_client as factory

    return factory(**kwargs)


def parse_page1(path):
    from ingestion.page1_parser import parse_page1 as parse

    return parse(path)


def drive_call(name, *args):
    from ingestion import drive_sync

    return getattr(drive_sync, name)(*args)


def download(*args):
    return drive_call("download", *args)


def find_files(*args):
    return drive_call("find_files", *args)


def read_state(*args):
    return drive_call("read_state", *args)


def upload_blob(*args):
    return drive_call("upload_blob", *args)


def allowed_pdf(url):
    try:
        p = urlsplit(url)
        return (
            official_url(url) and p.path.lower().endswith(".pdf") and not p.query and not p.fragment
        )
    except (ValueError, TypeError):
        return False


def select_candidates(worklist, journal):
    """Archive dates are matching hints, never verified operational dates."""
    gaps = {i["operational_date"] for i in worklist["items"]}
    hint_to_gaps = {}
    for gap in sorted(gaps):
        following = (date.fromisoformat(gap) + timedelta(days=1)).isoformat()
        for hint in (gap, following):
            hint_to_gaps.setdefault(hint, set()).add(gap)
    candidates = {}

    def add(url, dates, basis, expected=None):
        if not allowed_pdf(url):
            return
        item = candidates.setdefault(
            url,
            {
                "url": url,
                "candidate_gap_dates": set(),
                "match_basis": set(),
                "journal_sha256": None,
                "registered_sha256": set(),
            },
        )
        item["candidate_gap_dates"].update(dates)
        item["match_basis"].add(basis)
        if expected and re.fullmatch(r"[a-f0-9]{64}", expected):
            item["journal_sha256"] = expected
            if basis.startswith("registered_"):
                item["registered_sha256"].add(expected)

    # Preserve registered operational-date/version evidence as well as hint candidates.
    for gap in worklist["items"]:
        for source in gap["sources"]:
            add(source["url"], [gap["operational_date"]], "registered_date_link", source["sha256"])
        for source in gap["archive_hint_candidates"]:
            add(
                source["url"],
                [gap["operational_date"]],
                "registered_archive_hint",
                source["sha256"],
            )
    db = sqlite3.connect(journal.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Journal integrity check failed")
        rows = db.execute("""SELECT s.url,s.metadata,r.sha256 FROM sources s
            LEFT JOIN revisions r ON r.id=(SELECT MAX(r2.id) FROM revisions r2 WHERE r2.url=s.url)
            ORDER BY s.url""").fetchall()
    finally:
        db.close()
    for row in rows:
        metadata = json.loads(row["metadata"])
        if metadata.get("category") != "page_1":
            continue
        matching = hint_to_gaps.get(metadata.get("archive_date_hint"), set())
        if matching:
            add(row["url"], matching, "journal_same_or_next_day_hint", row["sha256"])
    result = []
    for item in candidates.values():
        item["candidate_gap_dates"] = sorted(item["candidate_gap_dates"])
        item["match_basis"] = sorted(item["match_basis"])
        item["registered_sha256"] = sorted(item["registered_sha256"])
        result.append(item)
    return sorted(result, key=lambda i: (i["candidate_gap_dates"][0], i["url"]))


def first_page_text(path):
    import pdfplumber

    from ingestion.page1_parser import extract_page_text

    with pdfplumber.open(path) as pdf:
        if not pdf.pages:
            return ""
        return extract_page_text(pdf.pages[0])[0]


def preserve_candidate(client, service, folder_id, candidate, output):
    """Prefer already archived original bytes; re-download current source only if needed."""
    path = output / "candidate.pdf"
    expected = candidate["journal_sha256"]
    archived = find_files(service, folder_id, "blob", expected) if expected else []
    retrieval = "verified_drive_blob" if archived else "current_official_url"
    if archived:
        download(service, archived[0]["id"], path)
        if digest(path) != expected:
            raise ValueError("Archived candidate checksum mismatch")
    else:
        data, _ = request_bytes(client, candidate["url"], MAX_BYTES)
        if not data or b"%PDF-" not in data[:1024]:
            raise ValueError("Official response is not a nonempty PDF")
        path.write_bytes(data)
    sha = digest(path)
    # Each version is content-addressed and verified remotely; no old PDF is replaced.
    blob = upload_blob(service, folder_id, path)
    if blob["sha256"] != sha:
        raise ValueError("Preserved PDF checksum mismatch")
    result = {
        **candidate,
        "retrieval": retrieval,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": sha,
        "size_bytes": path.stat().st_size,
        "drive_pdf": blob,
        "matches_saved_checksum": sha == expected if expected else None,
        "status": "preserved_pdf_pending_parse",
        "canonical_action": "none",
    }
    # PDF bytes are preserved even when parsing fails or an unsupported layout is encountered.
    try:
        extraction = parse_page1(path)
        record = {"extraction": extraction}
        checks = check_record(record)
        parsed_day = extraction["operational_date"]
        result.update(
            extraction=extraction,
            validation_issues=checks,
            parsed_date_is_candidate_gap=parsed_day in candidate["candidate_gap_dates"],
            status="parsed_candidate_needs_review"
            if (
                parsed_day in candidate["candidate_gap_dates"]
                and not extraction["issues"]
                and not checks
                and result["matches_saved_checksum"] is not False
            )
            else "held_for_source_review",
        )
    except Exception as exc:
        result.update(status="parse_failed_or_unsupported", parse_error_type=type(exc).__name__)
        code = getattr(exc, "code", None)
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_]{1,100}", code):
            result["parse_error_code"] = code
    try:
        text = first_page_text(path)
        if text:
            text_path = output / "first_page.txt"
            text_path.write_text(text[:100000], encoding="utf-8")
            result["drive_first_page_text"] = upload_blob(service, folder_id, text_path)
            result["text_truncated"] = len(text) > 100000
    except Exception as exc:
        result["text_diagnostic_error_type"] = type(exc).__name__
    return result


def investigate(worklist, candidates, client, service, folder_id, output, offset, max_files):
    selected = candidates[offset : offset + max_files]
    results = []
    for i, candidate in enumerate(selected, 1):
        folder = output / ("pdf_" + str(i).zfill(3))
        folder.mkdir()
        try:
            result = preserve_candidate(client, service, folder_id, candidate, folder)
        except Exception as exc:
            result = {
                **candidate,
                "status": "retrieval_or_preservation_failed",
                "error_type": type(exc).__name__,
                "canonical_action": "none",
            }
        results.append(result)
        (folder / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Investigation {i}/{len(selected)}: {result['status']}", flush=True)
    represented = {day for c in candidates for day in c["candidate_gap_dates"]}
    all_gaps = {i["operational_date"] for i in worklist["items"]}
    try:
        pdf_runtime = version("pdfplumber")
    except PackageNotFoundError:
        pdf_runtime = None
    report = {
        "rule_version": RULE_VERSION,
        "parser_source_sha256": digest(Path(__file__).with_name("page1_parser.py")),
        "pdfplumber_version": pdf_runtime,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "worklist_id": worklist["worklist_id"],
        "window": worklist["window"],
        "gap_dates": len(all_gaps),
        "candidate_urls": len(candidates),
        "offset": offset,
        "max_files": max_files,
        "selected_urls": len(selected),
        "next_offset": offset + len(selected) if offset + len(selected) < len(candidates) else None,
        "gap_dates_without_known_candidates": sorted(all_gaps - represented),
        "candidate_plan_sha256": hashlib.sha256(
            json.dumps(candidates, sort_keys=True).encode()
        ).hexdigest(),
        "status_counts": dict(Counter(r["status"] for r in results)),
        "results": results,
        "canonical_records_promoted": 0,
        "measurements_inserted": 0,
        "limitations": [
            "This is targeted evidence collection, not a backup of the full historical archive.",
            "Source hints and parser dates are not independent original-PDF verification.",
            "No known candidate does not prove an absent official report.",
            "Current bytes can differ from earlier journal versions; versions remain distinct.",
            "Parsed candidates remain unapproved; no Neon records or daily checkpoints change.",
            "Candidate order can change after journal updates; compare plan fingerprints.",
            "All-file scope, retries and archive rediscovery remain bounded manual follow-ups.",
        ],
    }
    (output / "investigation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def drive_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    secrets = ROOT / "secrets"
    config = json.loads((secrets / "google_drive_config.json").read_text())
    credentials = Credentials.from_authorized_user_file(
        str(secrets / "google_drive_token.json"), ["https://www.googleapis.com/auth/drive.file"]
    )
    credentials.refresh(Request())
    return build("drive", "v3", credentials=credentials, cache_discovery=False), config["folder_id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--max-files", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    if not 1 <= args.max_files <= 50 or not 0 <= args.offset <= 10000:
        parser.error("Use max-files 1..50 and offset 0..10000")
    if args.start_date > args.end_date or (args.end_date - args.start_date).days >= 3660:
        parser.error("Use an ordered window of at most 3660 calendar days")
    output = (
        ROOT
        / "data/recovery_online"
        / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8])
    )
    output.mkdir(parents=True)
    with contextmanager(read_session)() as session:
        worklist = read_worklist(session, args.start_date, args.end_date)
    (output / "worklist.json").write_text(json.dumps(worklist, indent=2), encoding="utf-8")
    service, folder_id = drive_service()
    try:
        _, state, _ = read_state(service, folder_id)
        if state is None:
            raise ValueError("A verified collection journal checkpoint is required")
        journal = output / "collection.sqlite3"
        download(service, state["journal"]["id"], journal)
        if digest(journal) != state["journal"]["sha256"]:
            raise ValueError("Journal checksum mismatch")
        candidates = select_candidates(worklist, journal)
        (output / "candidate_plan.json").write_text(
            json.dumps(candidates, indent=2), encoding="utf-8"
        )
        with create_client(timeout=20) as client:
            report = investigate(
                worklist,
                candidates,
                client,
                service,
                folder_id,
                output,
                args.offset,
                args.max_files,
            )
        # Upload the report after the PDFs. Never replace the daily checkpoint.
        report_blob = upload_blob(service, folder_id, output / "investigation.json")
        manifest = {
            "schema_version": 1,
            "worklist": upload_blob(service, folder_id, output / "worklist.json"),
            "candidate_plan": upload_blob(service, folder_id, output / "candidate_plan.json"),
            "report": report_blob,
            "journal_sha256": state["journal"]["sha256"],
        }
        (output / "storage_receipt.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        upload_blob(service, folder_id, output / "storage_receipt.json")
    finally:
        service.close()
    summary = {
        k: report[k]
        for k in (
            "window",
            "gap_dates",
            "candidate_urls",
            "selected_urls",
            "offset",
            "next_offset",
            "status_counts",
            "canonical_records_promoted",
        )
    }
    summary["drive_preservation"] = "verified"
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    # Retrieval failures are disclosed and make the job need attention, after report preservation.
    return 1 if report["status_counts"].get("retrieval_or_preservation_failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
