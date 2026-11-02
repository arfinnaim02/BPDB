"""Read-only registered evidence for gaps; never infer official-report absence."""

import re
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.api.monitoring import Database, MasterDay, canonical_query, materialize_days
from app.db.models import DailyReport, ExtractionIssue, ReportVersion, SourceDocument, VersionSource

router = APIRouter(prefix="/api/v1/dataset", tags=["Source audit"])
DETAIL_LIMIT = 10
ISSUE_LIMIT = 20
SAMPLE_LIMIT = 32


class SourceEvidence(BaseModel):
    id: str
    url: str
    sha256: str
    status: str
    report_date_metadata: date | None
    archive_date_hint: date | None


class VersionEvidence(BaseModel):
    id: str
    report_id: str
    quality_status: str
    is_current: bool
    parser_version: str


class IssueEvidence(BaseModel):
    id: str
    source_id: str
    version_id: str | None
    code: str
    severity: str
    resolved: bool
    checks: list[str]


class GapAuditDay(BaseModel):
    operational_date: date
    assessment: str
    findings: list[str]
    source_report_status: str = "not_assessed"
    report_ids: list[str]
    version_count: int
    versions: list[VersionEvidence]
    source_count: int
    sources: list[SourceEvidence]
    archive_hint_count: int
    archive_hint_candidates: list[SourceEvidence]
    issue_count: int
    issues: list[IssueEvidence]


class UndatedSource(BaseModel):
    source: SourceEvidence
    issue_count: int
    issues: list[IssueEvidence]


class AuditReport(BaseModel):
    scope: str = "Registered Neon evidence; no source files are reparsed or changed"
    generated_at: datetime
    canonical_dates: int
    earliest_operational_date: date | None
    latest_operational_date: date | None
    missing_dates: int
    gap_page: int
    gap_page_size: int
    gap_total_pages: int
    gap_items: list[GapAuditDay]
    undated_source_count: int
    source_page: int
    source_page_size: int = 10
    source_total_pages: int
    undated_sources: list[UndatedSource]
    sample_policy: str = (
        "Earliest and latest canonical date per year, at most 32 dates. "
        "Confirm legacy/modern layouts manually; this is not a random accuracy estimate."
    )
    sample_candidate_dates: int
    sample_review_status: str = "verification_not_recorded_here"
    samples: list[MasterDay]
    sample_error: str | None = None
    limitation: str = (
        "Missing or absent registered evidence does not prove an official report is missing. "
        "Archive hints are not operational dates. Historical local quarantines and failed "
        "downloads may not be registered in Neon. Evidence states are not established causes."
    )


def source_view(source: SourceDocument) -> SourceEvidence:
    return SourceEvidence(
        id=source.id,
        url=source.original_url,
        sha256=source.sha256,
        status=source.status,
        report_date_metadata=source.report_date,
        archive_date_hint=source.archive_date_hint,
    )


def safe_code(value, fallback="unclassified") -> str:
    return (
        value
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_]{1,100}", value)
        else fallback
    )


def issue_view(issue: ExtractionIssue) -> IssueEvidence:
    details = issue.details if isinstance(issue.details, dict) else {}
    checks = details.get("issues")
    checks = checks if isinstance(checks, list) else []
    codes = sorted({safe_code(item.get("code")) for item in checks if isinstance(item, dict)})
    return IssueEvidence(
        id=issue.id,
        source_id=issue.source_id,
        version_id=issue.version_id,
        code=safe_code(issue.code),
        severity=safe_code(issue.severity),
        resolved=issue.resolved_at is not None,
        checks=codes[:20],
    )


def read_audit(
    session: Session, gap_page: int = 1, gap_page_size: int = 20, source_page: int = 1
) -> AuditReport:
    if (
        not 1 <= gap_page <= 100000
        or not 1 <= gap_page_size <= 50
        or not 1 <= source_page <= 100000
    ):
        raise HTTPException(422, "Invalid audit pagination")
    rows = session.execute(canonical_query().order_by(DailyReport.report_date)).all()
    first = rows[0].operational_date if rows else None
    last = rows[-1].operational_date if rows else None
    # Count and page missing dates using ranges, without expanding an unbounded calendar.
    gap_ranges = []
    missing = 0
    for previous, following in zip(rows, rows[1:]):
        length = (following.operational_date - previous.operational_date).days - 1
        if length:
            gap_ranges.append((previous.operational_date + timedelta(days=1), length))
            missing += length
    offset = (gap_page - 1) * gap_page_size
    selected = []
    for start, length in gap_ranges:
        if offset >= length:
            offset -= length
            continue
        count = min(length - offset, gap_page_size - len(selected))
        selected.extend(start + timedelta(days=offset + i) for i in range(count))
        offset = 0
        if len(selected) == gap_page_size:
            break
    reports = (
        session.scalars(
            select(DailyReport).where(
                DailyReport.dataset_grain == "national_daily",
                DailyReport.report_date.in_(selected),
            )
        ).all()
        if selected
        else []
    )
    report_map = {report.id: report for report in reports}
    versions = (
        session.scalars(
            select(ReportVersion)
            .where(ReportVersion.report_id.in_(report_map))
            .order_by(ReportVersion.report_id, ReportVersion.version_number)
        ).all()
        if reports
        else []
    )
    version_map = {version.id: version for version in versions}
    links = (
        session.execute(
            select(VersionSource.version_id, SourceDocument)
            .join(SourceDocument, SourceDocument.id == VersionSource.source_id)
            .where(VersionSource.version_id.in_(version_map), SourceDocument.category == "page_1")
        ).all()
        if versions
        else []
    )
    candidates = (
        session.scalars(
            select(SourceDocument)
            .where(
                SourceDocument.category == "page_1",
                or_(
                    SourceDocument.report_date.in_(selected),
                    SourceDocument.archive_date_hint.in_(selected),
                ),
            )
            .order_by(SourceDocument.original_url, SourceDocument.id)
        ).all()
        if selected
        else []
    )

    # Sources held for review with neither report_date metadata nor a national version link.
    dated_link = exists(
        select(VersionSource.source_id)
        .join(ReportVersion, VersionSource.version_id == ReportVersion.id)
        .join(DailyReport, ReportVersion.report_id == DailyReport.id)
        .where(
            VersionSource.source_id == SourceDocument.id,
            DailyReport.dataset_grain == "national_daily",
        )
    )
    queue = select(SourceDocument).where(
        SourceDocument.category == "page_1",
        SourceDocument.report_date.is_(None),
        SourceDocument.status.in_(["quarantined", "review_required", "failed"]),
        ~dated_link,
    )
    queue_total = session.scalar(select(func.count()).select_from(queue.subquery())) or 0
    queue_sources = session.scalars(
        queue.order_by(SourceDocument.retrieved_at.desc(), SourceDocument.id)
        .offset((source_page - 1) * 10)
        .limit(10)
    ).all()
    sources = {source.id: source for _, source in links}
    sources.update({source.id: source for source in candidates})
    sources.update({source.id: source for source in queue_sources})
    issues = (
        session.scalars(
            select(ExtractionIssue)
            .where(
                or_(
                    ExtractionIssue.source_id.in_(sources),
                    ExtractionIssue.version_id.in_(version_map),
                )
            )
            .order_by(ExtractionIssue.created_at, ExtractionIssue.id)
        ).all()
        if sources or versions
        else []
    )

    items = []
    for day in selected:
        day_reports = [r for r in reports if r.report_date == day]
        day_report_ids = {r.id for r in day_reports}
        day_versions = [v for v in versions if v.report_id in day_report_ids]
        day_version_ids = {v.id for v in day_versions}
        linked_sources = {s.id: s for version_id, s in links if version_id in day_version_ids}
        direct = {s.id: s for s in candidates if s.report_date == day}
        direct.update(linked_sources)
        hints = [s for s in candidates if s.archive_date_hint == day and s.id not in direct]
        day_issues = [
            issue
            for issue in issues
            if (
                issue.version_id in day_version_ids
                or (issue.version_id is None and issue.source_id in direct)
            )
        ]
        findings = []
        if day_reports:
            findings.append("national_report_row_registered")
        findings.extend(sorted({"version_" + v.quality_status for v in day_versions}))
        findings.extend(
            sorted(
                {
                    "source_" + s.status
                    for s in direct.values()
                    if s.status in ("quarantined", "review_required", "failed")
                }
            )
        )
        if direct:
            findings.append("date_linked_source_metadata")
        if any(issue.resolved_at is None for issue in day_issues):
            findings.append("unresolved_extraction_issues")
        assessment = (
            "registered_evidence"
            if day_reports or direct
            else ("archive_hints_only" if hints else "no_date_linked_evidence")
        )
        items.append(
            GapAuditDay(
                operational_date=day,
                assessment=assessment,
                findings=findings,
                report_ids=sorted(day_report_ids),
                version_count=len(day_versions),
                versions=[
                    VersionEvidence(
                        id=v.id,
                        report_id=v.report_id,
                        quality_status=v.quality_status,
                        is_current=report_map[v.report_id].current_version_id == v.id,
                        parser_version=v.parser_version,
                    )
                    for v in day_versions[:DETAIL_LIMIT]
                ],
                source_count=len(direct),
                sources=[
                    source_view(s)
                    for s in sorted(direct.values(), key=lambda s: (s.original_url, s.id))[
                        :DETAIL_LIMIT
                    ]
                ],
                archive_hint_count=len(hints),
                archive_hint_candidates=[source_view(s) for s in hints[:DETAIL_LIMIT]],
                issue_count=len(day_issues),
                issues=[issue_view(i) for i in day_issues[:ISSUE_LIMIT]],
            )
        )
    held = []
    for source in queue_sources:
        source_issues = [issue for issue in issues if issue.source_id == source.id]
        held.append(
            UndatedSource(
                source=source_view(source),
                issue_count=len(source_issues),
                issues=[issue_view(i) for i in source_issues[:ISSUE_LIMIT]],
            )
        )

    # A reproducible review plan; selecting evidence is not recording a completed PDF audit.
    by_year = {}
    for row in rows:
        by_year.setdefault(row.operational_date.year, []).append(row)
    sample_map = {}
    for values in by_year.values():
        for row in (values[0], values[-1]):
            sample_map[row.version_id] = row
    sample_rows = sorted(sample_map.values(), key=lambda row: row.operational_date)
    sample_count = len(sample_rows)
    if sample_count > SAMPLE_LIMIT:
        sample_rows = [
            sample_rows[round(i * (sample_count - 1) / (SAMPLE_LIMIT - 1))]
            for i in range(SAMPLE_LIMIT)
        ]
    sample_error = None
    try:
        samples = materialize_days(session, sample_rows) if sample_rows else []
    except HTTPException as exc:
        if exc.status_code != 503:
            raise
        samples = []
        sample_error = (
            "Canonical sample evidence failed a consistency check; "
            "inspect source links and measurements."
        )
    return AuditReport(
        generated_at=datetime.now(timezone.utc),
        canonical_dates=len(rows),
        earliest_operational_date=first,
        latest_operational_date=last,
        missing_dates=missing,
        gap_page=gap_page,
        gap_page_size=gap_page_size,
        gap_total_pages=(missing + gap_page_size - 1) // gap_page_size,
        gap_items=items,
        undated_source_count=queue_total,
        source_page=source_page,
        source_total_pages=(queue_total + 9) // 10,
        undated_sources=held,
        sample_candidate_dates=sample_count,
        samples=samples,
        sample_error=sample_error,
    )


@router.get("/audit", response_model=AuditReport)
def audit(
    response: Response,
    session: Database,
    gap_page: Annotated[int, Query(ge=1, le=100000)] = 1,
    gap_page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    source_page: Annotated[int, Query(ge=1, le=100000)] = 1,
) -> AuditReport:
    response.headers["Cache-Control"] = "no-store"
    return read_audit(session, gap_page, gap_page_size, source_page)
