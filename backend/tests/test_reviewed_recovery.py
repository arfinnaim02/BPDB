"""Synthetic database gates; real PDF regression fixtures are tested separately."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from app.db.models import DailyReport, ReportVersion, VersionSource
from ingestion import reviewed_recovery as recovery
from ingestion.page1_parser import parse_page1_text
from test_quality import seed


def record():
    review = recovery.REVIEW[0]
    extraction = parse_page1_text((Path(__file__).parent / "fixtures/page1_geometry/7390page1.txt")
                                 .read_text(encoding="utf-8"))
    return {"source_url": "https://misc.bpdb.gov.bd/storage/daily_archive/" + review[0],
            "source_sha256": review[1], "extraction": extraction}


def staged(session):
    item = record()
    report, version, source = seed(session, date(2024, 1, 1), row=False, quality="partial")
    report.current_version_id = None
    version.parser_version = recovery.KEY
    source.original_url = item["source_url"]
    source.sha256 = item["source_sha256"]
    for o in item["extraction"]["observations"]:
        table, unit, period, dimensions = recovery.METRICS[o["metric"]]
        session.add(table(version_id=version.id, source_id=source.id, metric=o["metric"],
                          unit=unit, period=period, zone="national", value=Decimal(o["value"]),
                          source_page=1, raw_text=o["raw_text"], **dimensions))
    session.flush()
    return item, report, version, source


def test_exact_readback_and_missing_source(session):
    with pytest.raises(ValueError, match="already be registered"):
        recovery.inspect_stage(session, record())
    item, report, version, _ = staged(session)
    assert recovery.inspect_stage(session, item, required=True)[1].id == version.id
    assert report.current_version_id is None


@pytest.mark.parametrize("field,value", [("value", Decimal(1)), ("zone", "other"),
    ("period", "other"), ("unit", "bad"), ("source_page", 2), ("raw_text", "changed")])
def test_every_measurement_dimension_is_verified(session, field, value):
    item, _, version, _ = staged(session)
    row = session.scalar(recovery.select(recovery.TABLES[0]).where(
        recovery.TABLES[0].version_id == version.id))
    setattr(row, field, value)
    session.flush()
    with pytest.raises(ValueError, match="mismatch"):
        recovery.inspect_stage(session, item, required=True)


def test_missing_link_and_competing_canonical_are_blocked(session):
    item, report, version, source = staged(session)
    session.delete(session.get(VersionSource, (version.id, source.id)))
    session.flush()
    with pytest.raises(ValueError, match="mismatch"):
        recovery.inspect_stage(session, item)
    other = ReportVersion(report_id=report.id, version_number=2,
                          quality_status="validated", parser_version="other")
    session.add(other)
    session.flush()
    report.current_version_id = other.id
    session.flush()
    with pytest.raises(ValueError, match="replacement is forbidden"):
        recovery.inspect_stage(session, item)


def test_promote_and_repeat_without_duplicates(session):
    item, report, version, _ = staged(session)

    class Factory:
        @contextmanager
        def begin(self):
            with session.begin_nested():
                yield session

    assert recovery.transact(Factory(), [item], "verify")["verified_measurements"] == 5
    assert report.current_version_id is None
    assert recovery.transact(Factory(), [item], "promote")["promoted"] == 1
    assert report.current_version_id == version.id
    result = recovery.transact(Factory(), [item], "promote")
    assert result["promoted"] == 0 and result["already_canonical"] == 1
    assert len(list(session.scalars(recovery.select(DailyReport)))) == 1


def test_checksum_gate_before_parse(tmp_path):
    path = tmp_path / "wrong.pdf"
    path.write_bytes(b"%PDF-wrong")
    with pytest.raises(ValueError, match="checksum"):
        recovery.validate_pdf(path, recovery.REVIEW[0])


def test_real_import_staging_is_idempotent_and_does_not_promote(session, monkeypatch):
    item = record()
    report, old, source = seed(session, date(2024, 1, 1), row=False, quality="quarantined")
    report.current_version_id = None
    source.original_url, source.sha256 = item["source_url"], item["source_sha256"]
    session.flush()
    execute = session.execute

    def sqlite_execute(statement, *args, **kwargs):
        # SQLite has no advisory lock; all importer ORM writes still execute.
        if str(statement).startswith("SELECT pg_advisory_xact_lock"):
            return None
        return execute(statement, *args, **kwargs)

    monkeypatch.setattr(session, "execute", sqlite_execute)

    class Factory:
        @contextmanager
        def begin(self):
            with session.begin_nested():
                yield session

    result = recovery.transact(Factory(), [item], "stage")
    assert result["inserted_measurements"] == 5 and result["promoted"] == 0
    assert report.current_version_id is None and old.quality_status == "quarantined"
    assert recovery.transact(Factory(), [item], "stage")["inserted_measurements"] == 0
    assert recovery.transact(Factory(), [item], "verify")["verified_measurements"] == 5


@pytest.mark.parametrize("alter", ["date", "value", "parser", "unit", "issues"])
def test_exact_extraction_gate(tmp_path, monkeypatch, alter):
    item = record()["extraction"]
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"synthetic bytes; parser mocked")
    review = list(recovery.REVIEW[0])
    review[1] = recovery.hashlib.sha256(pdf.read_bytes()).hexdigest()
    if alter == "date":
        item["operational_date"] = "2024-01-02"
    elif alter == "value":
        item["observations"][0]["value"] = "1"
    elif alter == "parser":
        item["parser_version"] = "unexpected"
    elif alter == "unit":
        item["observations"][0]["unit"] = "bad"
    else:
        item["issues"] = [{"code": "synthetic_issue"}]
    monkeypatch.setattr(recovery, "parse_page1", lambda _: item)
    with pytest.raises(ValueError, match="reviewed extraction"):
        recovery.validate_pdf(pdf, review)
