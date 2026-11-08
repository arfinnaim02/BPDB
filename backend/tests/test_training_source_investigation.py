from research.investigate_training_sources import annotate, scoped_worklist


def inputs():
    study = {
        "study_id": "frozen-study",
        "register": [
            {
                "date": "2020-01-04",
                "category": "review_held",
                "source_id": "energy-source",
                "source_sha256": "a" * 64,
                "original_value": "1",
                "review_flags": "low_energy_to_peak_ratio",
            },
            {"date": "2021-01-01", "category": "no_canonical_record"},
            {"date": "2022-01-01", "category": "no_canonical_record"},
        ],
    }
    live = {
        "worklist_id": "live-id",
        "items": [
            {"operational_date": "2021-01-01", "sources": [], "archive_hint_candidates": []},
            {"operational_date": "2024-01-01", "sources": [], "archive_hint_candidates": []},
        ],
    }
    original = [
        {
            "operational_date": "2020-01-04",
            "sources": [
                {
                    "id": "energy-source",
                    "url": "https://misc.bpdb.gov.bd/source.pdf",
                    "sha256": "a" * 64,
                },
                {
                    "id": "unrelated",
                    "url": "https://misc.bpdb.gov.bd/other.pdf",
                    "sha256": "b" * 64,
                },
            ],
        }
    ]
    return study, live, original


def test_scope_reconciles_frozen_dates_without_claiming_values_verified():
    study, live, original = inputs()
    worklist, ledger = scoped_worklist(study, live, original)
    assert [r["operational_date"] for r in worklist["items"]] == ["2020-01-04", "2021-01-01"]
    assert len(worklist["items"][0]["sources"]) == 1
    assert worklist["items"][0]["sources"][0]["id"] == "energy-source"
    assert ledger[-1]["current_assessment"] == (
        "canonical_date_now_present_energy_not_independently_verified"
    )
    assert all(not row["repair_approved"] for row in ledger)
    assert scoped_worklist(study, live, original)[0]["worklist_id"] == worklist["worklist_id"]


def test_successful_parse_never_clears_hold_or_approves_changed_bytes():
    study, live, original = inputs()
    _, ledger = scoped_worklist(study, live, original)
    report = {
        "results": [
            {
                "sha256": "b" * 64,
                "status": "parsed_candidate_needs_review",
                "extraction": {
                    "operational_date": "2020-01-04",
                    "observations": [{"metric": "energy_generated", "value": "201"}],
                },
            }
        ]
    }
    result = annotate(report, ledger)
    candidate = result["results"][0]
    assert candidate["frozen_energy_value"] == "1"
    assert candidate["reparsed_energy_value"] == "201"
    assert not candidate["matches_frozen_sha256"]
    assert candidate["review_resolution"].startswith("not_approved")
    assert result["source_correction_approvals"] == result["measurements_inserted"] == 0
    assert result["canonical_records_promoted"] == 0
    assert result["retraining_performed"] is False


def test_missing_frozen_source_is_not_invented_and_parse_failure_stays_unapproved():
    study, live, _ = inputs()
    worklist, ledger = scoped_worklist(study, live, [])
    assert worklist["items"][0]["sources"] == []
    result = annotate({"results": [{"status": "parse_failed_or_unsupported"}]}, ledger)
    assert result["results"][0]["review_resolution"] == "candidate_only_not_approved"
