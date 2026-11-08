"""Verify/interpret a source-investigation artifact; never approve or import repairs."""

import argparse
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from app.api.measurement_review import screen
from app.api.preparation import encode
from app.api.recovery import worklist_identity
from app.api.treatment import load_study


def summarize(folder):
    report_bytes = (folder / "investigation.json").read_bytes()
    report = json.loads(report_bytes)
    worklist = json.loads((folder / "worklist.json").read_bytes())
    plan = json.loads((folder / "candidate_plan.json").read_bytes())
    receipt = json.loads((folder / "storage_receipt.json").read_bytes())
    study = load_study()
    if report["study_id"] != study["study_id"]:
        raise ValueError("Investigation/study mismatch")
    if report["worklist_id"] != worklist_identity(worklist):
        raise ValueError("Worklist changed")
    if (
        report["candidate_plan_sha256"]
        != hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    ):
        raise ValueError("Candidate plan changed")
    for name in ("worklist.json", "candidate_plan.json", "investigation.json"):
        data = (folder / name).read_bytes()
        expected = receipt[name]
        if len(data) != expected["size"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError("Retained report receipt differs")
    if (
        any(
            report[k] != 0
            for k in (
                "measurements_inserted",
                "canonical_records_promoted",
                "source_correction_approvals",
            )
        )
        or report["retraining_performed"]
    ):
        raise ValueError("Investigation must have zero imports, approvals and retraining")
    preserved, text_checks = 0, 0
    for index, result in enumerate(report["results"], 1):
        if result["status"] == "retrieval_or_preservation_failed":
            continue
        blob = result["drive_pdf"]
        if blob["sha256"] != result["sha256"] or blob["size"] != result["size_bytes"]:
            raise ValueError("Preserved original PDF receipt differs")
        preserved += 1
        text = folder / ("pdf_" + str(index).zfill(3)) / "first_page.txt"
        if text.exists():
            expected = result["drive_first_page_text"]
            data = text.read_bytes()
            if (
                len(data) != expected["size"]
                or hashlib.sha256(data).hexdigest() != expected["sha256"]
            ):
                raise ValueError("Text diagnostic differs from preserved evidence")
            text_checks += 1
    assessed = {r["date"]: r for r in report["frozen_register_assessment"]}
    if set(assessed) != {r["date"] for r in study["register"]}:
        raise ValueError("Affected-date coverage differs")
    rows = []
    for original in study["register"]:
        day = original["date"]
        candidates = [p for p in plan if day in p["candidate_gap_dates"]]
        results = [r for r in report["results"] if day in r["candidate_gap_dates"]]
        matching = [r for r in results if r.get("extraction", {}).get("operational_date") == day]
        evidence = []
        for item in matching:
            extraction = item["extraction"]
            values = {o["metric"]: Decimal(o["value"]) for o in extraction["observations"]}
            flags, ratio = screen(
                {
                    k: v
                    for k, v in values.items()
                    if k
                    in (
                        "energy_generated",
                        "maximum_generation",
                        "minimum_generation",
                        "day_peak_generation",
                        "evening_peak_generation",
                    )
                }
            )
            unchanged_bytes = (
                item.get("sha256") == original["source_sha256"]
                if original["category"] == "review_held"
                else None
            )
            energy = values.get("energy_generated")
            clear_screen = not flags and energy is not None and not extraction["issues"]
            evidence.append(
                {
                    "url": item["url"],
                    "sha256": item.get("sha256"),
                    "retrieval": item.get("retrieval"),
                    "status": item["status"],
                    "parsed_operational_date": day,
                    "parsed_energy_value": str(energy) if energy is not None else None,
                    "screen_flags": [f.code for f in flags],
                    "energy_to_peak_ratio": ratio,
                    "matches_frozen_source_bytes": unchanged_bytes,
                    "candidate_passes_parse_and_screen": (
                        clear_screen
                        and not item["validation_issues"]
                        and item["status"] == "parsed_candidate_needs_review"
                        and unchanged_bytes is not False
                    ),
                    "approved": False,
                }
            )
        plausible = [e for e in evidence if e["candidate_passes_parse_and_screen"]]
        if assessed[day]["current_assessment"].startswith("canonical_date_now_present"):
            state = "canonical_date_now_present_energy_not_independently_verified"
        elif plausible:
            state = "source_derived_candidate_requires_independent_review"
        elif matching:
            state = "matching_source_still_held_or_revision_requires_review"
        elif not candidates:
            state = "not_located_in_retained_candidate_evidence"
        elif not results:
            state = "known_candidates_not_in_this_bounded_batch"
        elif all(r["status"] == "retrieval_or_preservation_failed" for r in results):
            state = "retrieval_failed_not_proof_of_missing_report"
        else:
            state = "candidate_wrong_date_or_unparsed_requires_follow_up"
        rows.append(
            {
                **original,
                "assessment": state,
                "candidate_urls": len(candidates),
                "attempted_urls": len(results),
                "matching_sources": evidence,
                "repair_approved": False,
            }
        )
    pdfs = []
    for file in sorted(folder.glob("pdf_*/candidate.pdf")):
        result = json.loads(file.with_name("result.json").read_bytes())
        if hashlib.sha256(file.read_bytes()).hexdigest() != result["sha256"]:
            raise ValueError("Artifact PDF differs from preserved source")
        pdfs.append({"path": str(file.relative_to(folder)), "sha256": result["sha256"]})
    summary = {
        "schema_version": 1,
        "study_id": study["study_id"],
        "investigation_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "candidate_plan_sha256": report["candidate_plan_sha256"],
        "journal_sha256": report["journal_sha256"],
        "affected_dates": len(rows),
        "frozen_absent_dates": sum(r["category"] == "no_canonical_record" for r in rows),
        "frozen_held_dates": sum(r["category"] == "review_held" for r in rows),
        "candidate_urls": len(plan),
        "attempted_urls": len(report["results"]),
        "attempted_source_urls": [r["url"] for r in report["results"]],
        "next_offset": report["next_offset"],
        "assessment_counts": dict(Counter(r["assessment"] for r in rows)),
        "retrieval_status_counts": report["status_counts"],
        "artifact_pdf_checksums_verified": pdfs,
        "preserved_pdf_receipts_verified": preserved,
        "text_diagnostics_checksum_verified": text_checks,
        "repairs_approved": 0,
        "measurements_written": 0,
        "forecast_models_fit": 0,
        "dates": rows,
        "limitations": [
            "A passing parse and heuristic screen are not independent original-PDF approval.",
            "No candidate in retained evidence does not establish that no official PDF exists.",
            "Present canonical date does not independently verify its energy measurement.",
            "The original treatment study and canonical dataset remain unchanged.",
        ],
    }
    summary["assessment_id"] = hashlib.sha256(encode(summary)).hexdigest()
    return summary


def combine(batches):
    """Combine independently verified, disjoint batches from the exact same plan."""
    if not batches:
        raise ValueError("No verified batches")
    first = batches[0]
    for report in batches:
        if any(
            report[k] != first[k]
            for k in (
                "study_id",
                "candidate_plan_sha256",
                "candidate_urls",
                "affected_dates",
            )
        ):
            raise ValueError("Candidate plan/study changed; do not blindly continue offsets")
    attempted = [url for b in batches for url in b["attempted_source_urls"]]
    if len(attempted) != len(set(attempted)):
        raise ValueError("Overlapping batches would double-count attempts")
    rows = []
    for original in first["dates"]:
        parts = [next(r for r in b["dates"] if r["date"] == original["date"]) for b in batches]
        evidence = [e for r in parts for e in r["matching_sources"]]
        attempts = sum(r["attempted_urls"] for r in parts)
        if any(r["assessment"].startswith("canonical_date_now_present") for r in parts):
            state = "canonical_date_now_present_energy_not_independently_verified"
        elif any(e["candidate_passes_parse_and_screen"] for e in evidence):
            state = "source_derived_candidate_requires_independent_review"
        elif evidence:
            state = "matching_source_still_held_or_revision_requires_review"
        elif original["candidate_urls"] == 0:
            state = "not_located_in_retained_candidate_evidence"
        elif attempts == 0:
            state = "known_candidates_not_in_this_bounded_batch"
        elif all(
            r["attempted_urls"] == 0 or r["assessment"].startswith("retrieval_failed")
            for r in parts
        ):
            state = "retrieval_failed_not_proof_of_missing_report"
        else:
            state = "candidate_wrong_date_or_unparsed_requires_follow_up"
        rows.append(
            {
                **original,
                "attempted_urls": attempts,
                "matching_sources": evidence,
                "assessment": state,
            }
        )
    status = Counter()
    for batch in batches:
        status.update(batch["retrieval_status_counts"])
    result = {
        "schema_version": 1,
        "study_id": first["study_id"],
        "candidate_plan_sha256": first["candidate_plan_sha256"],
        "source_report_sha256s": [b["investigation_sha256"] for b in batches],
        "affected_dates": first["affected_dates"],
        "frozen_absent_dates": first["frozen_absent_dates"],
        "frozen_held_dates": first["frozen_held_dates"],
        "candidate_urls": first["candidate_urls"],
        "attempted_urls": len(attempted),
        "all_retained_candidate_urls_attempted": len(attempted) == first["candidate_urls"],
        "assessment_counts": dict(Counter(r["assessment"] for r in rows)),
        "retrieval_status_counts": dict(status),
        "artifact_pdfs_checksum_verified": sum(
            len(b["artifact_pdf_checksums_verified"]) for b in batches
        ),
        "preserved_pdf_receipts_verified": sum(
            b["preserved_pdf_receipts_verified"] for b in batches
        ),
        "text_diagnostics_checksum_verified": sum(
            b["text_diagnostics_checksum_verified"] for b in batches
        ),
        "repairs_approved": 0,
        "measurements_written": 0,
        "forecast_models_fit": 0,
        "dates": rows,
        "limitations": first["limitations"],
    }
    result["assessment_id"] = hashlib.sha256(encode(result)).hexdigest()
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--additional-folder", type=Path, action="append", default=[])
    args = p.parse_args()
    batches = [summarize(folder) for folder in [args.folder, *args.additional_folder]]
    result = combine(batches) if args.additional_folder else batches[0]
    args.output.write_bytes(encode(result))
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k
                not in (
                    "dates",
                    "artifact_pdf_checksums_verified",
                    "limitations",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
