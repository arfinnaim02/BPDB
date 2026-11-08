"""Investigate frozen treatment gaps and holds; read-only Neon, no model fitting."""

import argparse
import io
import json
import zipfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from app.api.preparation import encode
from app.api.recovery import read_worklist, worklist_identity
from app.api.treatment import load_study
from ingestion import online_recovery as recovery

from research.treatment_study import BUNDLE_SHA


def scoped_worklist(study, live, original):
    by_date = {r["operational_date"]: r for r in original}
    live_gaps = {r["operational_date"]: r for r in live["items"]}
    items, ledger = [], []
    for row in study["register"]:
        day = row["date"]
        if row["category"] == "review_held":
            record = by_date.get(day, {})
            sources = [s for s in record.get("sources", []) if s["id"] == row["source_id"]]
            item = {
                "operational_date": day,
                "sources": sources,
                "archive_hint_candidates": [],
                "frozen_category": "review_held",
                "frozen_review_flags": row["review_flags"],
                "frozen_original_value": row["original_value"],
            }
            status = "frozen_hold_requires_original_review"
        elif day in live_gaps:
            item = {**live_gaps[day], "frozen_category": row["category"]}
            status = "still_absent_canonical_date"
        else:
            item = None
            status = "canonical_date_now_present_energy_not_independently_verified"
        if item is not None:
            items.append(item)
        ledger.append({**row, "current_assessment": status, "repair_approved": False})
    result = {
        "rule_version": "frozen_training_source_investigation_v1",
        "window": {"start_date": "2020-01-01", "end_date": "2023-12-31"},
        "study_id": study["study_id"],
        "live_worklist_id": live["worklist_id"],
        "items": items,
    }
    result["worklist_id"] = worklist_identity(result)
    return result, ledger


def annotate(report, ledger):
    held = {r["date"]: r for r in ledger if r["category"] == "review_held"}
    for result in report["results"]:
        day = result.get("extraction", {}).get("operational_date")
        frozen = held.get(day)
        if frozen:
            energy = next(
                (
                    o
                    for o in result["extraction"]["observations"]
                    if o["metric"] == "energy_generated"
                ),
                None,
            )
            result["matches_frozen_sha256"] = result.get("sha256") == frozen["source_sha256"]
            result["frozen_energy_value"] = frozen["original_value"]
            result["reparsed_energy_value"] = energy["value"] if energy else None
            result["review_resolution"] = "not_approved_requires_original_and_definition_review"
        else:
            result["review_resolution"] = "candidate_only_not_approved"
    report["frozen_register_assessment"] = ledger
    report["retraining_performed"] = False
    report["canonical_records_promoted"] = 0
    report["measurements_inserted"] = 0
    report["source_correction_approvals"] = 0
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-files", type=int, default=100)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument(
        "--output", type=Path, default=recovery.ROOT / "data/training_source_investigation"
    )
    args = p.parse_args()
    if not 1 <= args.max_files <= 100 or not 0 <= args.offset <= 10000:
        p.error("Bound files to 1..100 and offset to 0..10000")
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    study = load_study()
    with contextmanager(recovery.read_session)() as session:
        live = read_worklist(session, date(2020, 1, 1), date(2023, 12, 31))
    service, folder = recovery.drive_service()
    try:
        found = recovery.find_files(service, folder, "blob", BUNDLE_SHA)
        if len(found) != 1:
            raise ValueError("Exact frozen input unavailable")
        bundle = out / "frozen_input.zip"
        recovery.download(service, found[0]["id"], bundle)
        if recovery.digest(bundle) != BUNDLE_SHA:
            raise ValueError("Frozen input checksum differs")
        with zipfile.ZipFile(io.BytesIO(bundle.read_bytes())) as z:
            original = json.loads(z.read("original_snapshot.json"))
        worklist, ledger = scoped_worklist(study, live, original)
        _, state, _ = recovery.read_state(service, folder)
        if state is None:
            raise ValueError("Verified journal checkpoint required")
        journal = out / "collection.sqlite3"
        recovery.download(service, state["journal"]["id"], journal)
        if recovery.digest(journal) != state["journal"]["sha256"]:
            raise ValueError("Journal checksum differs")
        candidates = recovery.select_candidates(worklist, journal)
        held = {r["date"] for r in ledger if r["category"] == "review_held"}
        candidates.sort(
            key=lambda c: (
                not bool(held.intersection(c["candidate_gap_dates"])),
                c["candidate_gap_dates"][0],
                c["url"],
            )
        )
        (out / "worklist.json").write_bytes(encode(worklist))
        (out / "candidate_plan.json").write_bytes(encode(candidates))
        with recovery.create_client(timeout=20) as client:
            report = recovery.investigate(
                worklist,
                candidates,
                client,
                service,
                folder,
                out,
                args.offset,
                args.max_files,
            )
        annotate(report, ledger)
        report.update(study_id=study["study_id"], journal_sha256=state["journal"]["sha256"])
        (out / "investigation.json").write_bytes(encode(report))
        receipt = {
            name: recovery.upload_blob(service, folder, out / name)
            for name in ("worklist.json", "candidate_plan.json", "investigation.json")
        }
        (out / "storage_receipt.json").write_bytes(encode(receipt))
        recovery.upload_blob(service, folder, out / "storage_receipt.json")
        summary = {
            k: report[k]
            for k in (
                "study_id",
                "gap_dates",
                "candidate_urls",
                "selected_urls",
                "next_offset",
                "status_counts",
                "gap_dates_without_known_candidates",
                "canonical_records_promoted",
                "measurements_inserted",
                "source_correction_approvals",
            )
        }
        summary["frozen_affected_dates"] = len(ledger)
        summary["drive_preservation"] = "verified"
        (out / "summary.json").write_bytes(encode(summary))
        print(json.dumps(summary, indent=2))
        return 1 if report["status_counts"].get("retrieval_or_preservation_failed") else 0
    finally:
        service.close()


if __name__ == "__main__":
    raise SystemExit(main())
