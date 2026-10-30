from datetime import date

import pytest
from app.db.models import DailyReport, IngestionRun, ReportVersion, SourceDocument
from app.services.canonical import PromotionRejected, promote_version
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


def report(session, day=1):
    row = DailyReport(report_date=date(2026, 1, day), dataset_grain="national_daily")
    session.add(row)
    session.flush()
    return row


def version(session, row, number=1, quality="validated", reason=None):
    item = ReportVersion(
        report_id=row.id,
        version_number=number,
        quality_status=quality,
        parser_version="test-only",
        correction_reason=reason,
    )
    session.add(item)
    session.flush()
    return item


def test_unique_date_and_grain(session):
    report(session)
    with pytest.raises(IntegrityError):
        report(session)


def test_promotion_idempotent_and_correction_keeps_history(session):
    row = report(session)
    first = version(session, row)
    assert promote_version(session, row.id, first.id)
    assert not promote_version(session, row.id, first.id)
    second = version(session, row, 2, reason="Verified official correction: test fixture")
    with pytest.raises(PromotionRejected):
        promote_version(session, row.id, second.id)
    assert row.current_version_id == first.id
    assert promote_version(session, row.id, second.id, verified_correction=True)
    assert session.get(ReportVersion, first.id) is not None
    with pytest.raises(PromotionRejected):
        promote_version(session, row.id, first.id, verified_correction=True)


@pytest.mark.parametrize("quality", ["partial", "quarantined", "conflict"])
def test_bad_version_does_not_replace_valid(session, quality):
    row = report(session)
    first = version(session, row)
    promote_version(session, row.id, first.id)
    bad = version(session, row, 2, quality)
    with pytest.raises(PromotionRejected):
        promote_version(session, row.id, bad.id, verified_correction=True)
    assert row.current_version_id == first.id


def test_cross_report_pointer_rejected_by_database(session):
    first, second = report(session, 1), report(session, 2)
    foreign = version(session, second)
    first.current_version_id = foreign.id
    with pytest.raises(IntegrityError):
        session.flush()


def test_transaction_rollback(session):
    row = report(session)
    session.commit()
    item = version(session, row)
    promote_version(session, row.id, item.id)
    session.rollback()
    assert session.get(DailyReport, row.id).current_version_id is None
    assert session.scalar(select(ReportVersion)) is None


def test_duplicate_original_source_constraint(session):
    run = IngestionRun(trigger="test")
    session.add(run)
    session.flush()

    def source():
        return SourceDocument(
            original_url="https://misc.bpdb.gov.bd/test.pdf",
            category="summary",
            sha256="a" * 64,
            storage_key="test-only.pdf",
            original_filename="test.pdf",
            content_type="application/pdf",
            size_bytes=10,
            ingestion_run_id=run.id,
        )

    session.add(source())
    session.flush()
    session.add(source())
    with pytest.raises(IntegrityError):
        session.flush()
