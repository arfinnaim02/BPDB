"""Synthetic export checks; hosted acceptance verifies actual Neon data."""

import copy
import hashlib
import io
import zipfile
from datetime import date

import pytest
from app.api.monitoring import MasterMeasurement
from app.api.preparation import build_snapshot, bundle, encode
from ingestion.freeze_research import (
    END,
    START,
    TRAIN_END,
    VALIDATION_END,
    verify_bundle,
    verify_repairs,
)
from ingestion.reviewed_recovery import FIELDS, METRICS, REVIEW, SPRING_REVIEW
from test_preparation import day


def synthetic_snapshot():
    days = []
    for review in (*REVIEW, *SPRING_REVIEW):
        name, sha, when, _, values = review[:5]
        d = day((date.fromisoformat(when) - START).days + 1)
        d.sources[0].url = "https://misc.bpdb.gov.bd/storage/daily_archive/" + name
        d.sources[0].sha256 = sha
        d.measurements = [MasterMeasurement(
            metric=metric, value=value, unit=METRICS[metric][1], zone="national",
            period=METRICS[metric][2], fuel=None, source_id=d.sources[0].id,
            source_page=1, raw_text="Synthetic test value " + value,
        ) for metric, value in zip(FIELDS, values, strict=True)]
        days.append(d)
    return build_snapshot(days, "energy_generated", START, END, TRAIN_END, VALIDATION_END)


def test_full_calendar_identity_csv_agreement_and_all_repair_lineage():
    snapshot = synthetic_snapshot()
    manifest, original, audit = verify_bundle(bundle(snapshot))
    assert manifest["snapshot_id"] == snapshot["snapshot_id"]
    assert len(audit) == 366 and len(original) == 4
    assert verify_repairs(original) == ["2024-01-01", "2024-01-04", "2024-04-20", "2024-05-25"]
    assert sum(s["estimated_training_days"] for s in manifest["splits"].values()) == 0
    assert all(not r["prepared_train_value"] for r in audit if r["split"] != "train")


def test_corrupt_file_is_rejected():
    data = bundle(synthetic_snapshot())
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as original, zipfile.ZipFile(out, "w") as modified:
        for name in original.namelist():
            modified.writestr(
                name, b"changed" if name == "daily_values.csv" else original.read(name)
            )
    with pytest.raises(ValueError, match="checksum"):
        verify_bundle(out.getvalue())


@pytest.mark.parametrize("case", ["missing_date", "wrong_value", "wrong_sha", "wrong_period"])
def test_repair_gate_rejects_missing_or_changed_provenance(case):
    original = copy.deepcopy(synthetic_snapshot()["original"])
    if case == "missing_date":
        original.pop()
    elif case == "wrong_value":
        original[0]["measurements"][0]["value"] = "1"
    elif case == "wrong_sha":
        original[0]["sources"][0]["sha256"] = "0" * 64
    else:
        original[0]["measurements"][0]["period"] = "wrong"
    with pytest.raises(ValueError):
        verify_repairs(original)


def test_recomputed_checksums_do_not_hide_changed_split_or_heldout_value():
    snapshot = synthetic_snapshot()
    snapshot["rows"][-1]["prepared_train_value"] = "999"
    with pytest.raises(ValueError, match="split isolation"):
        verify_bundle(bundle(snapshot))
    snapshot = synthetic_snapshot()
    snapshot["config"]["train_end"] = "2024-05-31"
    snapshot["snapshot_id"] = hashlib.sha256(encode({
        "config": snapshot["config"], "original": snapshot["original"]
    })).hexdigest()
    with pytest.raises(ValueError, match="cutoffs"):
        verify_bundle(bundle(snapshot))
