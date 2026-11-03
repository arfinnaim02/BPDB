import hashlib
import json
import sqlite3
from datetime import date

import pytest
from app.api.audit import read_audit
from app.api.monitoring import read_session
from app.api.recovery import read_worklist, worklist_identity
from app.core.config import Settings
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from ingestion.reconcile_gaps import load_worklist, local_path, reconcile
from test_audit import source
from test_quality import seed


def test_filtered_window_inside_gap_retains_edge_days_and_scope(session):
    seed(session, date(2024, 1, 1))
    seed(session, date(2024, 1, 10))
    r = read_audit(session, start_date=date(2024, 1, 3), end_date=date(2024, 1, 5))
    assert r.missing_dates == 3 and r.canonical_dates_in_window == 0
    assert r.selected_start_date == date(2024, 1, 3) and r.selected_end_date == date(2024, 1, 5)
    assert [i.operational_date for i in r.gap_items] == [date(2024, 1, n) for n in (3, 4, 5)]
    assert read_audit(session, start_date=date(2025, 1, 1)).gap_items == []
    with pytest.raises(HTTPException):
        read_audit(session, start_date=date(2024, 2, 1), end_date=date(2024, 1, 1))


def test_complete_worklist_is_not_limited_to_visible_page(session):
    seed(session, date(2024, 1, 1))
    seed(session, date(2024, 5, 1))
    r = read_worklist(session)
    assert r["missing_dates"] == r["exported_dates"] == len(r["items"]) == 120
    assert r["window"] == {"start_date": "2024-01-01", "end_date": "2024-05-01"}
    assert r["canonical_dates_in_window"] == 2
    assert r["worklist_id"] == worklist_identity(r)
    assert r["assessment_counts"] == {"no_date_linked_evidence": 120}
    assert not session.new and not session.dirty


def test_registered_details_disclose_truncation_and_do_not_infer_causes(session):
    seed(session, date(2024, 1, 1))
    seed(session, date(2024, 1, 3))
    for _ in range(12):
        source(session, hint=date(2024, 1, 2))
    result = read_worklist(session)
    row = result["items"][0]
    assert row["details_truncated"] and row["archive_hint_count"] == 12
    assert len(row["archive_hint_candidates"]) == 10
    assert row["source_report_status"] == "not_assessed"
    assert row["next_check"] == "confirm_operational_date_inside_hint_pdf"
    first_id = result["worklist_id"]
    source(session, report_date=date(2024, 1, 2))
    assert read_worklist(session)["worklist_id"] != first_id


def test_empty_and_oversize_recovery_scope(session):
    assert read_worklist(session)["items"] == []
    seed(session, date(2000, 1, 1))
    seed(session, date(2024, 1, 1))
    with pytest.raises(HTTPException) as e:
        read_worklist(session)
    assert e.value.status_code == 422


@pytest.fixture
def local_case(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    batch = tmp_path / "batch"
    (batch / "records").mkdir(parents=True)
    pdf = raw / "fixture.pdf"
    pdf.write_bytes(b"%PDF-test-fixture")
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    c = sqlite3.connect(raw / "collection.sqlite3")
    c.executescript(
        "CREATE TABLE sources(url TEXT,metadata TEXT); "
        "CREATE TABLE revisions(url TEXT,sha256 TEXT,path TEXT,size_bytes INTEGER);"
    )
    c.execute(
        "INSERT INTO sources VALUES(?,?)",
        (
            "https://example.org/a.pdf",
            json.dumps({"category": "page_1", "archive_date_hint": "2024-01-03"}),
        ),
    )
    c.execute(
        "INSERT INTO revisions VALUES(?,?,?,?)",
        ("https://example.org/a.pdf", sha, "fixture.pdf", pdf.stat().st_size),
    )
    c.commit()
    c.close()
    record = {
        "source_url": "https://example.org/a.pdf",
        "source_sha256": sha,
        "original_storage_path": "fixture.pdf",
        "archive_date_hint": "2024-01-03",
        "batch_status": "quarantined",
        "extraction": {
            "operational_date": "2024-01-02",
            "parser_version": "legacy_page1_v2",
            "issues": [{"code": "missing_metric"}],
        },
    }
    (batch / "records" / "record.json").write_text(json.dumps(record))
    payload = {
        "rule_version": "recovery_worklist_v1",
        "window": {"start_date": "2024-01-01", "end_date": "2024-01-04"},
        "missing_dates": 2,
        "exported_dates": 2,
        "items": [
            {"operational_date": f"2024-01-0{n}", "assessment": "no_date_linked_evidence"}
            for n in (2, 3)
        ],
    }
    payload["worklist_id"] = worklist_identity(payload)
    return raw, batch, payload, record


def test_local_exact_and_hint_matches_are_separate_and_read_only(local_case):
    raw, batch, payload, _ = local_case
    before = (raw / "collection.sqlite3").read_bytes()
    result = reconcile(payload, raw, batch)
    assert result["gap_dates"] == 2
    exact = result["items"][0]["exact_date_candidates"][0]
    assert exact["file_state"] == "verified_size_and_sha256"
    assert exact["batch_status"] == "quarantined" and exact["parser_issue_codes"] == [
        "missing_metric"
    ]
    assert result["items"][0]["local_assessment"] == "exact_extraction_date_candidates"
    assert (
        result["items"][1]["hint_candidates"][0]["operational_date_from_extraction"] == "2024-01-02"
    )
    assert result["items"][1]["local_assessment"] == "local_extraction_hint_candidates"
    assert before == (raw / "collection.sqlite3").read_bytes()
    assert (
        result["local_metadata_fingerprint"]
        == reconcile(payload, raw, batch)["local_metadata_fingerprint"]
    )


def test_journal_revision_and_file_integrity_failures_are_visible(local_case):
    raw, batch, payload, record = local_case
    (raw / "fixture.pdf").write_bytes(b"changed bytes")
    result = reconcile(payload, raw, batch)
    assert result["verified_file_states"] == {"size_mismatch": 1}
    record["source_sha256"] = "f" * 64
    (batch / "records" / "record.json").write_text(json.dumps(record))
    assert reconcile(payload, raw, batch)["verified_file_states"] == {"revision_not_in_journal": 1}


def test_unreadable_records_and_unknown_local_matches_are_not_pdf_absence(local_case):
    raw, batch, payload, _ = local_case
    (batch / "records" / "record.json").write_text("{bad")
    result = reconcile(payload, raw, batch)
    assert len(result["batch_records_unreadable"]) == 1
    assert result["items"][0]["local_assessment"] == "journal_hint_candidates_only"
    payload["items"] = [{"operational_date": "2024-02-01", "assessment": "no_date_linked_evidence"}]
    assert (
        reconcile(payload, raw, batch)["items"][0]["local_assessment"]
        == "no_local_date_candidate_found"
    )


@pytest.mark.parametrize("path", ["../outside.pdf", "C:\\outside.pdf", "/etc/passwd", ""])
def test_local_source_paths_cannot_escape_raw_archive(tmp_path, path):
    with pytest.raises(ValueError):
        local_path(tmp_path, path)


def test_worklist_identity_and_unique_dates_are_checked(tmp_path, local_case):
    _, _, payload, _ = local_case
    p = tmp_path / "worklist.json"
    p.write_text(json.dumps(payload))
    assert len(load_worklist(p)["items"]) == 2
    payload["items"][0]["operational_date"] = "2024-01-03"
    p.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="identity"):
        load_worklist(p)
    payload["worklist_id"] = worklist_identity(payload)
    p.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="unique"):
        load_worklist(p)


def test_endpoint_protection_and_export_content(session, monkeypatch):
    seed(session, date(2024, 1, 1))
    seed(session, date(2024, 1, 4))
    settings = Settings(_env_file=None, admin_api_key="recovery-test-only")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    payload = read_worklist(session, date(2024, 1, 2), date(2024, 1, 3))
    monkeypatch.setattr("app.api.recovery.read_worklist", lambda *args: payload)
    app.dependency_overrides[read_session] = lambda: None
    try:
        with TestClient(app) as client:
            url = "/api/v1/dataset/recovery-worklist"
            assert client.get(url).status_code == 401
            r = client.get(
                url,
                headers={"X-API-Key": "recovery-test-only"},
                params={"start_date": "2024-01-02", "end_date": "2024-01-03"},
            )
            assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
            assert r.json()["exported_dates"] == 2
            assert "PRIVATE_STORAGE" not in r.text
            assert (
                client.get(
                    url,
                    headers={"X-API-Key": "recovery-test-only"},
                    params={"start_date": "invalid-date"},
                ).status_code
                == 422
            )
    finally:
        app.dependency_overrides.clear()
