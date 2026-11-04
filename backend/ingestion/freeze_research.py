"""Freeze the observed-only 2024 research baseline with verified repair lineage.

Reads Neon in a repeatable-read/read-only transaction. Archives a separate
research artifact; never updates authoritative records or the daily checkpoint.
"""

import csv
import hashlib
import io
import json
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from app.api.monitoring import read_session
from app.api.preparation import bundle, encode, read_snapshot

from ingestion.reviewed_recovery import FIELDS, METRICS, REVIEW, SPRING_REVIEW

ROOT = Path(__file__).resolve().parents[2]
START, END = date(2024, 1, 1), date(2024, 12, 31)
TRAIN_END, VALIDATION_END = date(2024, 6, 30), date(2024, 9, 30)


def verify_bundle(data):
    """Reopen the produced bytes; validate identity, every file and dense calendar."""
    expected_files = {"manifest.json", "original_snapshot.json", "daily_audit.csv",
                      "daily_values.csv", "monthly_observed.csv"}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if set(archive.namelist()) != expected_files or len(archive.namelist()) != 5:
            raise ValueError("Unexpected or duplicate research bundle files")
        files = {name: archive.read(name) for name in expected_files}
    manifest = json.loads(files["manifest.json"])
    if set(manifest["files"]) != expected_files - {"manifest.json"}:
        raise ValueError("Incomplete research manifest")
    for name, spec in manifest["files"].items():
        if (len(files[name]) != spec["bytes"]
                or hashlib.sha256(files[name]).hexdigest() != spec["sha256"]):
            raise ValueError("Research file checksum mismatch")
    original = json.loads(files["original_snapshot.json"])
    identity = hashlib.sha256(encode({"config": manifest["config"], "original": original}))
    if identity.hexdigest() != manifest["snapshot_id"]:
        raise ValueError("Research snapshot identity mismatch")
    config = manifest["config"]
    if config["policy"] != "observed_only" or config["metric"] != "energy_generated":
        raise ValueError("Expected observed-only energy baseline")
    if any(config[key] != str(value) for key, value in (
            ("start_date", START), ("end_date", END),
            ("train_end", TRAIN_END), ("validation_end", VALIDATION_END))):
        raise ValueError("Unexpected research window or split cutoffs")
    audit = list(csv.DictReader(io.StringIO(files["daily_audit.csv"].decode("utf-8-sig"))))
    values = list(csv.DictReader(io.StringIO(files["daily_values.csv"].decode("utf-8-sig"))))
    calendar = [(START + timedelta(days=n)).isoformat() for n in range(366)]
    if [r["operational_date"] for r in audit] != calendar or len(values) != 366:
        raise ValueError("Research calendar is incomplete or unordered")
    original_by_date = {d["operational_date"]: d for d in original}
    if len(original_by_date) != len(original):
        raise ValueError("Duplicate original dates")
    for row, value_row in zip(audit, values, strict=True):
        day = date.fromisoformat(row["operational_date"])
        split = "train" if day <= TRAIN_END else "validation" if day <= VALIDATION_END else "test"
        source_day = original_by_date.get(day.isoformat())
        matches = ([m for m in source_day["measurements"] if m["metric"] == "energy_generated"]
                   if source_day else [])
        if len(matches) > 1:
            raise ValueError("Ambiguous original energy")
        expected = matches[0]["value"] if matches else None
        if (row["split"] != split or row["original_value"] != (expected or "")
                or row["method"] not in ("observed", "observed_held", "unfilled")
                or (split != "train" and row["prepared_train_value"])
                or (row["prepared_train_value"] and
                    row["prepared_train_value"] != row["original_value"])):
            raise ValueError("Research values or split isolation mismatch")
        if list(value_row.values()) != [row["operational_date"], row["original_value"],
                                       row["prepared_train_value"]]:
            raise ValueError("Clean numeric CSV does not match audited values")
    for split, counts in manifest["splits"].items():
        selected = [r for r in audit if r["split"] == split]
        expected_counts = {
            "calendar_days": len(selected),
            "observed_days": sum(r["state"] == "observed" for r in selected),
            "missing_days": sum(r["state"] != "observed" for r in selected),
            "review_held_days": sum(r["review_hold"] == "True" for r in selected),
            "observed_target_candidates": sum(r["observed_target_candidate"] == "True"
                                              for r in selected),
            "estimated_training_days": 0,
            "prepared_training_days": sum(bool(r["prepared_train_value"]) for r in selected),
        }
        if counts != expected_counts:
            raise ValueError("Research split counters disagree with audited rows")
    return manifest, original, audit


def verify_repairs(original):
    by_date = {d["operational_date"]: d for d in original}
    verified = []
    for review in (*REVIEW, *SPRING_REVIEW):
        name, sha, day, _, values = review[:5]
        source_day = by_date.get(day)
        if source_day is None:
            raise ValueError("Recovered date missing from research snapshot")
        sources = {s["id"]: s for s in source_day["sources"]}
        for metric, value in zip(FIELDS, values, strict=True):
            matches = [m for m in source_day["measurements"] if m["metric"] == metric]
            if len(matches) != 1:
                raise ValueError("Recovered measurement missing or duplicated")
            measurement = matches[0]
            source = sources.get(measurement["source_id"], {})
            if (measurement["value"] is None or Decimal(measurement["value"]) != Decimal(value)
                    or measurement["unit"] != METRICS[metric][1]
                    or measurement["source_page"] != 1
                    or (measurement["zone"], measurement["period"], measurement["fuel"])
                    != ("national", METRICS[metric][2], None)
                    or not measurement["raw_text"]
                    or source.get("sha256") != sha
                    or source.get("url") != (
                        "https://misc.bpdb.gov.bd/storage/daily_archive/" + name)):
                raise ValueError("Recovered value or PDF lineage mismatch")
        verified.append(day)
    return verified


def main():
    from ingestion.drive_sync import upload_blob
    from ingestion.online_recovery import drive_service

    with contextmanager(read_session)() as session:
        snapshot = read_snapshot(session, "energy_generated", START, END, TRAIN_END,
                                 VALIDATION_END, "observed_only", 1)
    data = bundle(snapshot)
    manifest, original, audit = verify_bundle(data)
    repairs = verify_repairs(original)
    summary = {
        "status": "verified", "snapshot_id": manifest["snapshot_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "calendar_days": len(audit), "canonical_dates": len(original),
        "missing_canonical_dates": sum(r["state"] == "no_canonical_record" for r in audit),
        "repaired_dates_verified": repairs, "repaired_measurements_verified": 20,
        "splits": manifest["splits"], "estimated_values": 0,
        "neon_writes": 0, "checkpoint_replaced": False,
        "bundle_sha256": hashlib.sha256(data).hexdigest(),
        "limitations": manifest["limitations"],
    }
    output = ROOT / "data" / "research_snapshots" / manifest["snapshot_id"]
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / "observed_2024.zip"
    archive_path.write_bytes(data)
    report_path = output / "verification.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    service, folder_id = drive_service()
    try:
        receipt = {"snapshot_id": manifest["snapshot_id"],
                   "bundle": upload_blob(service, folder_id, archive_path),
                   "verification": upload_blob(service, folder_id, report_path)}
        if receipt["bundle"]["sha256"] != summary["bundle_sha256"]:
            raise ValueError("Archived research bundle checksum mismatch")
        receipt_path = output / "storage_receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        upload_blob(service, folder_id, receipt_path)
    finally:
        service.close()
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
