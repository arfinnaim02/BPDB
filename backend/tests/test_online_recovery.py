import hashlib
import json
import sqlite3
from contextlib import nullcontext

import pytest
from ingestion import online_recovery as worker


def worklist():
    return {
        "worklist_id": "w" * 64,
        "window": {"start_date": "2024-01-01", "end_date": "2024-01-03"},
        "items": [{"operational_date": "2024-01-02", "sources": [], "archive_hint_candidates": []}],
    }


def journal(tmp_path):
    path = tmp_path / "journal.sqlite3"
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE sources(url TEXT, metadata TEXT);"
        "CREATE TABLE revisions(id INTEGER PRIMARY KEY,url TEXT,sha256 TEXT);"
    )
    rows = [
        ("https://misc.bpdb.gov.bd/storage/a.pdf", "page_1", "2024-01-03"),
        ("https://misc.bpdb.gov.bd/storage/b.pdf", "page_1", "2024-01-02"),
        ("https://misc.bpdb.gov.bd/storage/page2.pdf", "page_2", "2024-01-02"),
        ("https://evil.example/a.pdf", "page_1", "2024-01-02"),
        ("https://misc.bpdb.gov.bd/storage/future.pdf", "page_1", "2025-01-02"),
    ]
    for url, category, hint in rows:
        db.execute(
            "INSERT INTO sources VALUES(?,?)",
            (url, json.dumps({"category": category, "archive_date_hint": hint})),
        )
    db.execute("INSERT INTO revisions VALUES(1,?,?)", (rows[0][0], "a" * 64))
    db.execute("INSERT INTO revisions VALUES(2,?,?)", (rows[0][0], "b" * 64))
    db.commit()
    db.close()
    return path


def candidate(sha=None):
    return {
        "url": "https://misc.bpdb.gov.bd/storage/a.pdf",
        "candidate_gap_dates": ["2024-01-02"],
        "match_basis": ["journal_same_or_next_day_hint"],
        "journal_sha256": sha,
        "registered_sha256": [],
    }


def extraction(day="2024-01-02", issues=None):
    return {
        "operational_date": day,
        "issues": issues or [],
        "observations": [],
        "parser_version": "fixture",
        "quality_status": "pilot_extracted",
    }


def wire(monkeypatch, data=b"%PDF-fixture", parsed=None):
    calls = []
    monkeypatch.setattr(worker, "find_files", lambda *args: [])
    monkeypatch.setattr(worker, "request_bytes", lambda *args: (data, "application/pdf"))

    def upload(_, __, path):
        calls.append(path.name)
        return {
            "id": "remote-" + path.name,
            "sha256": worker.digest(path),
            "size": path.stat().st_size,
        }

    monkeypatch.setattr(worker, "upload_blob", upload)
    monkeypatch.setattr(worker, "parse_page1", lambda p: parsed or extraction())
    monkeypatch.setattr(worker, "check_record", lambda r: [])
    monkeypatch.setattr(worker, "first_page_text", lambda p: "original source page text")
    return calls


def test_candidate_selection_is_official_deduplicated_and_never_assigns_hint_as_date(tmp_path):
    path = journal(tmp_path)
    before = path.read_bytes()
    w = worklist()
    w["items"][0]["archive_hint_candidates"] = [
        {"url": "https://misc.bpdb.gov.bd/storage/a.pdf", "sha256": "a" * 64}
    ]
    result = worker.select_candidates(w, path)
    assert len(result) == 2 and result[0]["url"].endswith("a.pdf")
    assert result[0]["journal_sha256"] == "b" * 64
    assert result[0]["registered_sha256"] == ["a" * 64]
    assert result[0]["candidate_gap_dates"] == ["2024-01-02"]
    assert "journal_same_or_next_day_hint" in result[0]["match_basis"]
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "url",
    [
        "http://misc.bpdb.gov.bd/a.pdf",
        "https://example.org/a.pdf",
        "https://user:pass@misc.bpdb.gov.bd/a.pdf",
        "https://misc.bpdb.gov.bd:444/a.pdf",
        "https://misc.bpdb.gov.bd/a.pdf?token=secret",
        "https://misc.bpdb.gov.bd/a.pdf#x",
        "https://misc.bpdb.gov.bd/notpdf",
        "https://misc.bpdb.gov.bd:bad/a.pdf",
    ],
)
def test_only_fixed_official_https_pdf_urls_are_selected(url):
    assert not worker.allowed_pdf(url)


def test_new_pdf_and_diagnostic_text_are_preserved_without_any_canonical_action(
    tmp_path, monkeypatch
):
    calls = wire(monkeypatch)
    result = worker.preserve_candidate(None, None, "folder", candidate(), tmp_path)
    assert result["status"] == "parsed_candidate_needs_review"
    assert result["canonical_action"] == "none" and result["matches_saved_checksum"] is None
    assert calls == ["candidate.pdf", "first_page.txt"]
    assert result["drive_pdf"]["sha256"] == hashlib.sha256(b"%PDF-fixture").hexdigest()


def test_changed_bytes_and_wrong_parsed_date_are_held(tmp_path, monkeypatch):
    wire(monkeypatch)
    result = worker.preserve_candidate(None, None, "folder", candidate("f" * 64), tmp_path)
    assert (
        result["matches_saved_checksum"] is False and result["status"] == "held_for_source_review"
    )
    wire(monkeypatch, parsed=extraction("2024-01-03"))
    result = worker.preserve_candidate(None, None, "folder", candidate(), tmp_path)
    assert (
        not result["parsed_date_is_candidate_gap"] and result["status"] == "held_for_source_review"
    )


def test_verified_drive_pdf_is_reused_without_official_redownload(tmp_path, monkeypatch):
    data = b"%PDF-fixture"
    sha = hashlib.sha256(data).hexdigest()
    wire(monkeypatch)
    monkeypatch.setattr(worker, "find_files", lambda *args: [{"id": "existing"}])
    monkeypatch.setattr(worker, "download", lambda _, __, path: path.write_bytes(data))

    def forbidden(*args):
        raise AssertionError("must not fetch source URL when verified Drive bytes exist")

    monkeypatch.setattr(worker, "request_bytes", forbidden)
    result = worker.preserve_candidate(None, None, "folder", candidate(sha), tmp_path)
    assert result["retrieval"] == "verified_drive_blob" and result["matches_saved_checksum"]


def test_parse_failure_keeps_original_pdf_and_text_and_hides_raw_exception(tmp_path, monkeypatch):
    calls = wire(monkeypatch)

    def fail(path):
        raise ValueError("PRIVATE_EXCEPTION_TEXT")

    monkeypatch.setattr(worker, "parse_page1", fail)
    result = worker.preserve_candidate(None, None, "folder", candidate(), tmp_path)
    assert result["status"] == "parse_failed_or_unsupported"
    assert result["parse_error_type"] == "ValueError" and "candidate.pdf" in calls
    assert "PRIVATE_EXCEPTION_TEXT" not in json.dumps(result)
    assert result["drive_first_page_text"]


@pytest.mark.parametrize("data", [b"", b"<html>not pdf</html>"])
def test_empty_or_html_response_is_not_archived_as_pdf(tmp_path, monkeypatch, data):
    calls = wire(monkeypatch, data=data)
    with pytest.raises(ValueError):
        worker.preserve_candidate(None, None, "folder", candidate(), tmp_path)
    assert calls == []


def test_bounded_investigation_discloses_all_gaps_and_plan_progress(tmp_path, monkeypatch):
    wire(monkeypatch)
    candidates = [candidate(), {**candidate(), "url": "https://misc.bpdb.gov.bd/storage/b.pdf"}]
    report = worker.investigate(worklist(), candidates, None, None, "folder", tmp_path, 1, 1)
    assert report["selected_urls"] == 1 and report["offset"] == 1 and report["next_offset"] is None
    assert report["results"][0]["url"].endswith("b.pdf")
    assert report["canonical_records_promoted"] == report["measurements_inserted"] == 0
    assert (tmp_path / "investigation.json").is_file()
    assert len(report["candidate_plan_sha256"]) == 64


def test_main_preserves_manifest_and_report_without_checkpoint_update(tmp_path, monkeypatch):
    source_journal = journal(tmp_path)
    wire(monkeypatch)

    class Service:
        def close(self):
            pass

    monkeypatch.setattr(worker, "ROOT", tmp_path)
    monkeypatch.setattr(worker, "read_session", lambda: iter([None]))
    monkeypatch.setattr(worker, "read_worklist", lambda *args: worklist())
    monkeypatch.setattr(worker, "drive_service", lambda: (Service(), "folder"))
    monkeypatch.setattr(
        worker,
        "read_state",
        lambda *args: (
            None,
            {"journal": {"id": "journal", "sha256": worker.digest(source_journal)}},
            None,
        ),
    )
    monkeypatch.setattr(
        worker, "download", lambda _, __, path: path.write_bytes(source_journal.read_bytes())
    )
    monkeypatch.setattr(worker, "create_client", lambda **kwargs: nullcontext(None))
    monkeypatch.setattr(
        "sys.argv",
        [
            "online_recovery",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-03",
            "--max-files",
            "1",
        ],
    )
    assert worker.main() == 0
    folders = list((tmp_path / "data/recovery_online").iterdir())
    assert len(folders) == 1
    assert (folders[0] / "storage_receipt.json").is_file()
    assert json.loads((folders[0] / "summary.json").read_text())["drive_preservation"] == "verified"
    assert not (tmp_path / "data/raw/bpdb").exists()
