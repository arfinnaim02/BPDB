import hashlib
import json

import pytest
from app.api.preparation import encode
from app.api.recovery import worklist_identity
from research import summarize_training_sources as module


def seed(folder, monkeypatch):
    study = {
        "study_id": "study",
        "register": [
            {"date": "2020-01-04", "category": "review_held", "source_sha256": "a" * 64},
            {"date": "2020-01-05", "category": "no_canonical_record", "source_sha256": None},
        ],
    }
    monkeypatch.setattr(module, "load_study", lambda: study)
    worklist = {"rule_version": "test", "window": {}, "items": []}
    worklist["worklist_id"] = worklist_identity(worklist)
    plan = [{"url": "https://misc.bpdb.gov.bd/a.pdf", "candidate_gap_dates": ["2020-01-04"]}]
    result = {
        **plan[0],
        "sha256": "a" * 64,
        "retrieval": "verified_drive_blob",
        "status": "parsed_candidate_needs_review",
        "size_bytes": 100,
        "drive_pdf": {"sha256": "a" * 64, "size": 100},
        "validation_issues": [],
        "extraction": {
            "operational_date": "2020-01-04",
            "issues": [],
            "observations": [
                {"metric": "energy_generated", "value": "157.6"},
                {"metric": "maximum_generation", "value": "8397"},
            ],
        },
    }
    report = {
        "study_id": "study",
        "worklist_id": worklist["worklist_id"],
        "candidate_plan_sha256": hashlib.sha256(
            json.dumps(plan, sort_keys=True).encode()
        ).hexdigest(),
        "journal_sha256": "j" * 64,
        "next_offset": None,
        "results": [result],
        "status_counts": {"parsed_candidate_needs_review": 1},
        "measurements_inserted": 0,
        "canonical_records_promoted": 0,
        "source_correction_approvals": 0,
        "retraining_performed": False,
        "frozen_register_assessment": [
            {**r, "current_assessment": "pending"} for r in study["register"]
        ],
    }
    receipt = {}
    for name, value in (
        ("worklist.json", worklist),
        ("candidate_plan.json", plan),
        ("investigation.json", report),
    ):
        data = encode(value)
        (folder / name).write_bytes(data)
        receipt[name] = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    (folder / "storage_receipt.json").write_bytes(encode(receipt))


def test_source_candidate_and_absent_evidence_never_become_approved_repairs(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)
    report = module.summarize(tmp_path)
    assert report["affected_dates"] == 2
    assert report["dates"][0]["assessment"] == (
        "source_derived_candidate_requires_independent_review"
    )
    assert report["dates"][0]["matching_sources"][0]["parsed_energy_value"] == "157.6"
    assert report["dates"][1]["assessment"] == "not_located_in_retained_candidate_evidence"
    assert report["repairs_approved"] == 0
    assert all(not r["repair_approved"] for r in report["dates"])


def test_tampered_retained_report_or_pdf_is_rejected(tmp_path, monkeypatch):
    seed(tmp_path, monkeypatch)
    original = (tmp_path / "investigation.json").read_bytes()
    (tmp_path / "investigation.json").write_bytes(original + b" ")
    with pytest.raises(ValueError, match="receipt differs"):
        module.summarize(tmp_path)
    (tmp_path / "investigation.json").write_bytes(original)
    folder = tmp_path / "pdf_001"
    folder.mkdir()
    (folder / "candidate.pdf").write_bytes(b"not the preserved bytes")
    (folder / "result.json").write_text(json.dumps({"sha256": "a" * 64}))
    with pytest.raises(ValueError, match="PDF differs"):
        module.summarize(tmp_path)


def test_batch_merge_requires_stable_plan_and_disjoint_urls(tmp_path, monkeypatch):
    import copy

    seed(tmp_path, monkeypatch)
    first = module.summarize(tmp_path)
    first["candidate_urls"] = 2
    second = copy.deepcopy(first)
    second["attempted_source_urls"] = ["https://misc.bpdb.gov.bd/b.pdf"]
    second["dates"][0].update(attempted_urls=0, matching_sources=[])
    second["dates"][1].update(
        attempted_urls=1, assessment="candidate_wrong_date_or_unparsed_requires_follow_up"
    )
    combined = module.combine([first, second])
    assert combined["attempted_urls"] == 2
    assert combined["all_retained_candidate_urls_attempted"]
    assert combined["repairs_approved"] == 0
    assert len(combined["dates"][0]["matching_sources"]) == 1
    with pytest.raises(ValueError, match="Overlapping"):
        module.combine([first, first])
    second["candidate_plan_sha256"] = "changed"
    with pytest.raises(ValueError, match="plan/study changed"):
        module.combine([first, second])
