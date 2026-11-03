"""Complete date-gap evidence exports for local source investigation."""

import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone

from fastapi import APIRouter, Response
from sqlalchemy.orm import Session

from app.api.audit import DETAIL_LIMIT, ISSUE_LIMIT, read_audit
from app.api.monitoring import Database

router = APIRouter(prefix="/api/v1/dataset", tags=["Source recovery"])
RULE_VERSION = "recovery_worklist_v1"


def worklist_identity(payload):
    return hashlib.sha256(
        json.dumps(
            {k: payload[k] for k in ("rule_version", "window", "items")},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def read_worklist(session: Session, start_date=None, end_date=None):
    audit = read_audit(
        session, start_date=start_date, end_date=end_date, all_gaps=True, auxiliary=False
    )
    items = []
    for gap in audit.gap_items:
        evidence = gap.model_dump(mode="json")
        evidence["next_check"] = (
            "inspect_registered_versions_and_original_pdf"
            if gap.assessment == "registered_evidence"
            else "confirm_operational_date_inside_hint_pdf"
            if gap.assessment == "archive_hints_only"
            else "reconcile_local_journal_and_extraction_records"
        )
        evidence["details_truncated"] = (
            gap.version_count > len(gap.versions)
            or gap.source_count > len(gap.sources)
            or gap.archive_hint_count > len(gap.archive_hint_candidates)
            or gap.issue_count > len(gap.issues)
        )
        items.append(evidence)
    payload = {
        "rule_version": RULE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "window": {
            "start_date": str(audit.selected_start_date) if audit.selected_start_date else None,
            "end_date": str(audit.selected_end_date) if audit.selected_end_date else None,
        },
        "canonical_dates_in_window": audit.canonical_dates_in_window,
        "missing_dates": audit.missing_dates,
        "exported_dates": len(items),
        "assessment_counts": dict(Counter(i["assessment"] for i in items)),
        "detail_limits": {
            "versions_sources_hints_per_date": DETAIL_LIMIT,
            "issues_per_date": ISSUE_LIMIT,
        },
        "items": items,
        "limitations": [
            "All missing canonical dates in the selected bounded window are included.",
            "Registered detail lists are capped; counts and truncation flags disclose omissions.",
            "Archive hints are not verified operational dates; absence in Neon is not PDF absence.",
            "Historical local quarantines and failed downloads may be unregistered.",
            "This is a dated investigation snapshot, not an instruction to promote any record.",
            "Original PDFs, local files, source dates and measurements require verification.",
            "No downloads, reparsing, estimation or database writes occur in this endpoint.",
        ],
    }
    payload["worklist_id"] = worklist_identity(payload)
    return payload


@router.get("/recovery-worklist")
def recovery_worklist(
    response: Response,
    session: Database,
    start_date: date | None = None,
    end_date: date | None = None,
):
    payload = read_worklist(session, start_date, end_date)
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="bpdb-recovery-worklist.json"',
        },
    )
