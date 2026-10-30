"""Promotion only; extraction, validation and correction verification are separate gates."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DailyReport, ReportVersion


class PromotionRejected(ValueError):
    pass


def promote_version(
    session: Session,
    report_id: str,
    version_id: str,
    *,
    verified_correction: bool = False,
) -> bool:
    """Caller owns transaction. Row lock serializes concurrent canonical changes.

    This does not verify source authenticity. Only the future validation/review service
    may set quality_status=validated or invoke verified_correction=True.
    """
    report = session.scalar(
        select(DailyReport)
        .where(DailyReport.id == report_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    version = session.get(ReportVersion, version_id)
    if not report or not version or version.report_id != report_id:
        raise PromotionRejected("Version must belong to the target report")
    if version.quality_status != "validated":
        raise PromotionRejected("Only validated versions may be canonical")
    if report.current_version_id == version_id:
        return False
    if report.current_version_id:
        current = session.get(ReportVersion, report.current_version_id)
        if current is None or version.version_number <= current.version_number:
            raise PromotionRejected("Canonical revisions must advance version number")
        if not verified_correction or not version.correction_reason:
            raise PromotionRejected("Correction needs verification and a documented reason")
    report.current_version_id = version_id
    session.flush()
    return True
