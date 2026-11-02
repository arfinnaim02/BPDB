from datetime import date, datetime, timezone

import pytest
from app.api.audit import read_audit
from app.api.monitoring import read_session
from app.core.config import Settings
from app.db.models import ExtractionIssue, IngestionRun, SourceDocument
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_quality import seed


def boundaries(session):
    seed(session, date(2026, 1, 1))
    seed(session, date(2026, 1, 5))


def source(session, report_date=None, hint=None, status="quarantined", category="page_1"):
    run = IngestionRun(trigger="manual", status="succeeded")
    session.add(run)
    session.flush()
    document = SourceDocument(
        original_url=f"https://misc.bpdb.gov.bd/audit/{run.id}.pdf",
        category=category,
        sha256="b" * 64,
        storage_key="PRIVATE_STORAGE",
        original_filename="report.pdf",
        content_type="application/pdf",
        size_bytes=100,
        ingestion_run_id=run.id,
        report_date=report_date,
        archive_date_hint=hint,
        status=status,
    )
    session.add(document)
    session.flush()
    return document


def test_empty_audit_does_not_invent_dates_or_verification(session):
    result = read_audit(session)
    assert result.canonical_dates == 0 and result.missing_dates == 0
    assert result.earliest_operational_date is None
    assert result.gap_items == [] and result.samples == []
    assert result.sample_review_status == "verification_not_recorded_here"


def test_unknown_gaps_and_pagination(session):
    boundaries(session)
    result = read_audit(session, gap_page_size=2)
    assert result.missing_dates == 3 and result.gap_total_pages == 2
    assert [row.operational_date for row in result.gap_items] == [
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]
    assert all(row.assessment == "no_date_linked_evidence" for row in result.gap_items)
    second = read_audit(session, gap_page=2, gap_page_size=2)
    assert second.gap_items[0].operational_date == date(2026, 1, 4)
    assert second.gap_items[0].source_report_status == "not_assessed"
    assert read_audit(session, gap_page=3, gap_page_size=2).gap_items == []


def test_registered_versions_direct_dates_and_hint_only_remain_distinct(session):
    boundaries(session)
    _, version, linked = seed(session, date(2026, 1, 3), quality="partial")
    linked.status = "quarantined"
    direct = source(session, report_date=date(2026, 1, 4), status="review_required")
    hint = source(session, hint=date(2026, 1, 2))
    session.add_all(
        [
            ExtractionIssue(
                source_id=linked.id,
                version_id=version.id,
                code="partial_extraction",
                severity="error",
                details={"private": "PASSWORD_DO_NOT_EXPOSE"},
            ),
            ExtractionIssue(
                source_id=hint.id,
                code="daily_validation_failed",
                severity="error",
                details={"issues": [{"code": "missing_metric"}], "token": "HIDDEN_TOKEN"},
            ),
            ExtractionIssue(source_id=direct.id, code="review_required", severity="warning"),
        ]
    )
    session.flush()
    result = read_audit(session)
    hinted, partial, metadata = result.gap_items
    assert hinted.assessment == "archive_hints_only" and hinted.source_count == 0
    assert hinted.archive_hint_count == 1 and hinted.issue_count == 0
    assert partial.assessment == "registered_evidence"
    assert partial.versions[0].quality_status == "partial" and partial.versions[0].is_current
    assert "version_partial" in partial.findings
    assert partial.source_count == 1 and partial.sources[0].id == linked.id
    assert partial.issue_count == 1
    assert metadata.sources[0].id == direct.id and "source_review_required" in metadata.findings
    assert result.undated_source_count == 1
    assert result.undated_sources[0].issues[0].checks == ["missing_metric"]
    encoded = result.model_dump_json()
    for secret in ("PRIVATE_STORAGE", "PASSWORD_DO_NOT_EXPOSE", "HIDDEN_TOKEN"):
        assert secret not in encoded
    assert linked.status == "quarantined" and direct.status == "review_required"
    assert not session.dirty  # The audit never promotes or mutates evidence.


def test_wrong_grain_and_page_category_do_not_prove_a_gap_match(session):
    boundaries(session)
    seed(session, date(2026, 1, 2), quality="partial", grain="regional_daily")
    source(session, report_date=date(2026, 1, 2), hint=date(2026, 1, 2), category="page_2")
    result = read_audit(session)
    gap = result.gap_items[0]
    assert gap.assessment == "no_date_linked_evidence"
    assert gap.report_ids == [] and gap.version_count == 0 and gap.archive_hint_count == 0


def test_issue_for_another_version_is_not_assigned_from_a_hint(session):
    seed(session, date(2026, 1, 1))
    _, version, linked = seed(session, date(2026, 1, 3))
    linked.archive_date_hint = date(2026, 1, 2)
    session.add(
        ExtractionIssue(
            source_id=linked.id,
            version_id=version.id,
            code="old_issue",
            severity="warning",
        )
    )
    session.flush()
    gap = read_audit(session).gap_items[0]
    assert gap.assessment == "archive_hints_only" and gap.issue_count == 0


def test_source_queue_pages_and_resolved_issue_flags(session):
    for _ in range(11):
        source(session)
    result = read_audit(session, source_page=2)
    assert result.undated_source_count == 11 and result.source_total_pages == 2
    assert len(result.undated_sources) == 1
    selected = result.undated_sources[0].source
    session.add(
        ExtractionIssue(
            source_id=selected.id,
            code="resolved_issue",
            severity="warning",
            resolved_at=datetime.now(timezone.utc),
            details={"issues": ["bad", {"code": "x://secret"}]},
        )
    )
    session.flush()
    issue = read_audit(session, source_page=2).undated_sources[0].issues[0]
    assert issue.resolved and issue.checks == ["unclassified"]


def test_per_date_evidence_counts_show_when_details_are_capped(session):
    boundaries(session)
    for _ in range(12):
        source(session, report_date=date(2026, 1, 2))
    item = read_audit(session).gap_items[0]
    assert item.source_count == 12 and len(item.sources) == 10


def test_pdf_sample_plan_retains_source_provenance_and_is_not_verified(session):
    for day in [date(2020, 1, 1), date(2020, 6, 1), date(2020, 12, 31), date(2021, 1, 1)]:
        seed(session, day)
    result = read_audit(session)
    assert result.sample_candidate_dates == 3
    assert [s.operational_date for s in result.samples] == [
        date(2020, 1, 1),
        date(2020, 12, 31),
        date(2021, 1, 1),
    ]
    for sample in result.samples:
        assert sample.sources[0].sha256 == "a" * 64
        assert sample.measurements[0].source_id == sample.sources[0].id
    assert result.sample_review_status == "verification_not_recorded_here"


def test_inconsistent_sample_does_not_hide_gap_evidence(session):
    seed(session, date(2026, 1, 1), row=False)
    seed(session, date(2026, 1, 3))
    result = read_audit(session)
    assert result.sample_error and result.samples == []
    assert result.missing_dates == 1 and len(result.gap_items) == 1


def test_audit_auth_limits_and_serialization(monkeypatch, session):
    monkeypatch.setattr(
        "app.main.get_settings",
        lambda: Settings(
            _env_file=None,
            admin_api_key="audit-test-only",
        ),
    )
    data = read_audit(session)
    monkeypatch.setattr("app.api.audit.read_audit", lambda *_args: data)
    app.dependency_overrides[read_session] = lambda: None
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/dataset/audit").status_code == 401
            headers = {"X-API-Key": "audit-test-only"}
            for query in ("gap_page=0", "gap_page_size=51", "source_page=0"):
                assert (
                    client.get("/api/v1/dataset/audit?" + query, headers=headers).status_code == 422
                )
            response = client.get("/api/v1/dataset/audit", headers=headers)
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["sample_review_status"] == "verification_not_recorded_here"
    finally:
        app.dependency_overrides.pop(read_session, None)


def test_invalid_audit_pagination_is_rejected(session):
    with pytest.raises(HTTPException):
        read_audit(session, gap_page_size=51)


def test_sample_plan_is_bounded_and_retains_history_endpoints(session):
    for year in range(2000, 2018):
        seed(session, date(year, 1, 1))
        seed(session, date(year, 12, 31))
    result = read_audit(session)
    assert result.sample_candidate_dates == 36
    assert len(result.samples) == 32
    assert result.samples[0].operational_date == date(2000, 1, 1)
    assert result.samples[-1].operational_date == date(2017, 12, 31)
