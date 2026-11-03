"""Compare a downloaded gap worklist with local evidence. Never writes to Neon."""

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from uuid import uuid4

from app.api.recovery import RULE_VERSION, worklist_identity

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_worklist(path):
    if path.stat().st_size > 20_000_000:
        raise ValueError("Worklist exceeds 20 MB")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Invalid worklist document")
    if payload.get("rule_version") != RULE_VERSION:
        raise ValueError("Unsupported recovery worklist version")
    if payload.get("worklist_id") != worklist_identity(payload):
        raise ValueError("Recovery worklist identity mismatch; download it again")
    items = payload["items"]
    if len(items) > 3660 or len(items) != payload.get("missing_dates"):
        raise ValueError("Invalid or incomplete date worklist")
    dates = [date.fromisoformat(i["operational_date"]) for i in items]
    if dates != sorted(set(dates)) or len(items) != payload.get("exported_dates"):
        raise ValueError("Worklist dates must be complete, sorted and unique")
    if dates:
        start = date.fromisoformat(payload["window"]["start_date"])
        end = date.fromisoformat(payload["window"]["end_date"])
        if (end - start).days >= 3660 or not all(start <= d <= end for d in dates):
            raise ValueError("Worklist dates outside the bounded window")
    return payload


def local_path(root, value):
    """Resolve journal-relative paths without escaping the selected raw directory."""
    if (
        not isinstance(value, str)
        or not value
        or PureWindowsPath(value).drive
        or Path(value).is_absolute()
    ):
        raise ValueError("Unsafe local source path")
    path = (root / value.replace("\\", "/")).resolve()
    if path == root.resolve() or not path.is_relative_to(root.resolve()):
        raise ValueError("Unsafe local source path")
    return path


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_code(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_]{1,100}", value) else None


def reconcile(payload, raw_root, batch_root):
    journal = raw_root / "collection.sqlite3"
    if not journal.is_file() or not (batch_root / "records").is_dir():
        raise ValueError("Collection journal or selected batch records folder not found")
    # All saved revisions are considered; a later revision must not hide earlier evidence.
    connection = sqlite3.connect(journal.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        sources = connection.execute("SELECT url, metadata FROM sources ORDER BY url").fetchall()
        revisions = connection.execute(
            "SELECT url,sha256,path,size_bytes FROM revisions ORDER BY url,sha256,path"
        ).fetchall()
    finally:
        connection.close()
    revision_map = defaultdict(list)
    for r in revisions:
        revision_map[(r["url"], r["sha256"])].append(dict(r))
    metadata = {}
    journal_hints = defaultdict(list)
    for s in sources:
        info = json.loads(s["metadata"])
        if info.get("category") != "page_1":
            continue
        metadata[s["url"]] = info
        if info.get("archive_date_hint"):
            journal_hints[info["archive_date_hint"]].append(s["url"])
    records_by_date, records_by_hint = defaultdict(list), defaultdict(list)
    record_errors = []
    record_hashes = []
    for path in sorted((batch_root / "records").glob("*.json")):
        record_hashes.append((path.name, digest(path)))
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(record, dict) or not isinstance(record.get("extraction") or {}, dict):
                raise ValueError("Invalid extraction record schema")
            record["record_file"] = path.name
            extracted = record.get("extraction") or {}
            if extracted.get("operational_date"):
                operational = date.fromisoformat(extracted["operational_date"]).isoformat()
                records_by_date[operational].append(record)
            if record.get("archive_date_hint"):
                records_by_hint[record["archive_date_hint"]].append(record)
        except (ValueError, KeyError, TypeError):
            record_errors.append({"record_file": path.name, "code": "unreadable_record_json"})
    verified = {}

    def verify(record):
        key = (record.get("source_url"), record.get("source_sha256"))
        path_key = record.get("original_storage_path")
        cache_key = (*key, str(path_key))
        if cache_key in verified:
            return verified[cache_key]
        result = {
            "url": key[0],
            "sha256": key[1],
            "relative_path": path_key,
            "file_state": "revision_not_in_journal",
        }
        options = revision_map.get(key, [])
        if key[0] not in metadata:
            result["file_state"] = "page1_metadata_not_in_journal"
        elif options:
            try:
                path = local_path(raw_root, path_key)
                matches = [r for r in options if local_path(raw_root, r["path"]) == path]
                if not matches:
                    result["file_state"] = "record_path_not_in_matching_revision"
                elif not path.is_file():
                    result["file_state"] = "missing_local_file"
                elif not any(path.stat().st_size == r["size_bytes"] for r in matches):
                    result["file_state"] = "size_mismatch"
                elif digest(path) != key[1]:
                    result["file_state"] = "checksum_mismatch"
                else:
                    result["file_state"] = "verified_size_and_sha256"
            except (ValueError, OSError):
                result["file_state"] = "unsafe_or_unreadable_path"
        verified[cache_key] = result
        return result

    items = []
    for gap in payload["items"]:
        when = gap["operational_date"]
        next_day = (date.fromisoformat(when) + timedelta(days=1)).isoformat()
        exact = []
        for record in records_by_date[when]:
            extraction = record.get("extraction") or {}
            exact.append(
                {
                    **verify(record),
                    "record_file": record["record_file"],
                    "batch_status": safe_code(record.get("batch_status")),
                    "parser_version": safe_code(extraction.get("parser_version")),
                    "operational_date_from_extraction": when,
                    "parser_issue_codes": sorted(
                        {
                            safe_code(i.get("code")) or "unclassified"
                            for i in extraction.get("issues", [])
                            if isinstance(i, dict)
                        }
                    ),
                    "error_type": safe_code(record.get("error_type")),
                    "review_status": "not_verified_against_original_pdf",
                }
            )
        hints = []
        seen = set()
        for hint_date in (when, next_day):
            for record in records_by_hint[hint_date]:
                key = (record.get("source_url"), record.get("source_sha256"))
                if key in seen or any(e["url"] == key[0] and e["sha256"] == key[1] for e in exact):
                    continue
                seen.add(key)
                hints.append(
                    {
                        **verify(record),
                        "archive_date_hint": hint_date,
                        "record_file": record["record_file"],
                        "batch_status": safe_code(record.get("batch_status")),
                        "operational_date_from_extraction": (record.get("extraction") or {}).get(
                            "operational_date"
                        ),
                        "error_type": safe_code(record.get("error_type")),
                        "match_status": "hint_only_not_a_verified_date_match",
                    }
                )
        urls = sorted(set(journal_hints[when] + journal_hints[next_day]))
        assessment = (
            "exact_extraction_date_candidates"
            if exact
            else "local_extraction_hint_candidates"
            if hints
            else "journal_hint_candidates_only"
            if urls
            else "no_local_date_candidate_found"
        )
        items.append(
            {
                "operational_date": when,
                "local_assessment": assessment,
                "neon_assessment": gap["assessment"],
                "exact_date_candidates": exact,
                "hint_candidates": hints,
                "journal_hint_urls": urls,
                "decision": "pending_original_pdf_and_validation_review",
            }
        )
    return {
        "rule_version": "local_gap_reconciliation_v1",
        "worklist_id": payload["worklist_id"],
        "window": payload["window"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selected_batch": batch_root.name,
        "local_metadata_fingerprint": hashlib.sha256(
            json.dumps(
                {
                    "sources": [dict(s) for s in sources],
                    "revisions": [dict(r) for r in revisions],
                    "record_hashes": record_hashes,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest(),
        "batch_records_unreadable": record_errors,
        "gap_dates": len(items),
        "assessment_counts": dict(Counter(i["local_assessment"] for i in items)),
        "verified_file_states": dict(Counter(v["file_state"] for v in verified.values())),
        "items": items,
        "limitations": [
            "Extraction dates are stored parser claims, not independently verified PDF dates.",
            "Same-day and next-day archive hints are investigation candidates only.",
            "No local candidate found does not prove official source absence.",
            "SHA-256 verifies local bytes against the journal, not extraction accuracy.",
            "The selected batch may be incomplete or stale; it is never auto-selected.",
            "Worklist IDs detect content changes, not authenticity or current Neon state.",
            "No original files or journal records changed; "
            "no network requests, reparsing or Neon writes.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worklist", type=Path, required=True)
    parser.add_argument("--batch-folder", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, default=PROJECT_ROOT / "data/raw/bpdb")
    parser.add_argument(
        "--output-root", type=Path, default=PROJECT_ROOT / "data/processed/gap_recovery"
    )
    args = parser.parse_args()
    try:
        payload = load_worklist(args.worklist)
        report = reconcile(payload, args.raw_root, args.batch_folder)
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as exc:
        parser.exit(
            2,
            f"Recovery investigation stopped: {type(exc).__name__}. "
            "Check the worklist, journal and explicit batch paths. No data changed.\n",
        )
    output = args.output_root / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "local_reconciliation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "gap_dates",
                    "assessment_counts",
                    "verified_file_states",
                    "selected_batch",
                )
            }
            | {
                "report_file": str(output / "local_reconciliation.json"),
                "unreadable_batch_records": len(report["batch_records_unreadable"]),
                "status": "investigation_only_no_changes",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
