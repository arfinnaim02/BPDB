"""Synthetic safety tests; these are not the real treatment-study results."""

import csv
import hashlib
import io
import zipfile
from datetime import date, timedelta

import pytest
from research import treatment_study as study


def calendar():
    start = date(2020, 1, 1)
    return {
        start + timedelta(days=i): {
            "value": float(100 + i % 7),
            "original": str(100 + i % 7),
            "eligible": True,
            "available_at": None,
            "version_id": "version-" + str(i),
            "source_sha256": "source-" + str(i),
        }
        for i in range(2192)
    }


def test_wrong_frozen_bytes_rejected():
    with pytest.raises(ValueError, match="Frozen input bytes"):
        study.run(b"changed")


def test_policies_are_past_only_and_do_not_reuse_an_estimate():
    data = calendar()
    day = date(2021, 2, 10)
    result = study.estimate(data, day, "past_original_3")
    assert result["donor_last"] == str(day - timedelta(days=1))
    assert result["unknown_donor_times"] == 1
    for offset in range(1, 4):
        data[day - timedelta(days=offset)]["value"] = None
    data[day]["value"] = 9999
    data[day + timedelta(days=1)]["value"] = 9999
    assert study.estimate(data, day, "past_original_3") is None
    assert study.estimate(data, day, "observed_only") is None
    with pytest.raises(ValueError, match="Unknown"):
        study.estimate(data, day, "interpolate_future")


def test_known_late_and_review_held_donors_are_refused():
    data = calendar()
    day = date(2021, 2, 10)
    data[day - timedelta(days=1)]["available_at"] = "2021-02-12T00:00:00Z"
    data[day - timedelta(days=2)]["eligible"] = False
    data[day - timedelta(days=3)]["available_at"] = "2021-02-10T05:00:00Z"
    result = study.estimate(data, day, "past_original_3")
    assert result["donor_last"] == "2021-02-07"
    assert result["unknown_donor_times"] == 0


def test_median_minimum_donors_and_no_future_values():
    day = date(2021, 2, 10)
    data = calendar()
    for offset in (7, 14, 21):
        data[day - timedelta(days=offset)]["value"] = None
    assert study.estimate(data, day, "weekday_median_28") is None
    data[day - timedelta(days=14)]["value"] = 120
    result = study.estimate(data, day, "weekday_median_28")
    assert result["donor_count"] == 2
    before = study.estimate(data, day, "past_median_365")
    for d in data:
        if d >= day:
            data[d]["value"] = -999999
    assert study.estimate(data, day, "past_median_365") == before
    short = {d: row for d, row in data.items() if d >= day - timedelta(days=29)}
    assert study.estimate(short, day, "past_median_365") is None


@pytest.mark.parametrize("length", [1, 3, 7, 14, 30])
def test_mask_windows_are_deterministic_bounded_separated_and_original(length):
    data = calendar()
    data[date(2022, 5, 10)]["eligible"] = False
    blocks = study.mask_windows(data, length)
    assert blocks == study.mask_windows(data, length)
    assert 0 < len(blocks) <= 20
    for block in blocks:
        assert len(block) == length
        assert block[0] >= date(2020, 3, 31)
        assert block[-1] <= date(2023, 12, 29)
        assert block[0].year == block[-1].year
        assert all(data[d]["eligible"] for d in block)
    for first, second in zip(blocks, blocks[1:], strict=False):
        assert (second[0] - first[-1]).days >= 29


def synthetic_run(monkeypatch):
    data = calendar()
    held, missing = date(2021, 5, 3), date(2021, 5, 4)
    data[held].update(eligible=False, value=None, original=None)
    data[missing].update(eligible=False, value=None, original=None)
    rows = [
        {
            "operational_date": str(d),
            "review_hold": str(d == held),
            "state": "observed" if d != missing else "no_canonical_record",
            "original_value": row["original"] or "",
            "review_flags": "held" if d == held else "",
            "version_id": row["version_id"],
            "source_id": "source-id",
        }
        for d, row in data.items()
    ]
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("daily_audit.csv", study.csv_data(rows))
    bundle = stream.getvalue()
    monkeypatch.setattr(study, "BUNDLE_SHA", hashlib.sha256(bundle).hexdigest())
    monkeypatch.setattr(
        study.r1,
        "read_input",
        lambda _: ({"snapshot_id": study.SNAPSHOT_ID}, data, {"2020": {}, "2025": {}}),
    )
    return study.run(bundle)


def test_end_to_end_excludes_later_years_held_labels_and_recursive_donors(monkeypatch):
    report, exports = synthetic_run(monkeypatch)
    assert report["checks"]["training_days"] == 1461
    assert report["checks"]["all_donors_strictly_past"]
    assert report["checks"]["all_masks_eligible_training_originals"]
    assert report["checks"]["forecast_models_trained"] == 0
    assert report["checks"]["database_writes"] == 0
    assert list(report["training_coverage"]) == ["2020"]
    trials = list(csv.DictReader(io.StringIO(exports["masked_trials"].decode("utf-8-sig"))))
    hidden = {}
    for row in trials:
        hidden.setdefault(row["block_days"], set()).add(row["date"])
    for row in trials:
        assert row["date"] <= "2023-12-29"
        assert row["donor_last"] not in hidden[row["block_days"]]
        if row["donor_last"]:
            assert row["donor_last"] < row["date"]
    candidates = list(csv.DictReader(io.StringIO(exports["input_candidates"].decode("utf-8-sig"))))
    held = [r for r in candidates if r["date"] == "2021-05-03"]
    assert all(r["candidate_input_value"] == "" and r["status"] == "withheld" for r in held)
    assert all(r["original_value"] == "" for r in candidates if r["candidate_input_value"])
    baseline = [s for s in report["summaries"] if s["policy"] == "observed_only"]
    assert all(s["coverage_percent"] == 0 and s["conditional"]["mae"] is None for s in baseline)
    long = [s for s in report["summaries"] if s["block_days"] == 30]
    assert len({s["filled_days"] for s in long}) > 1
    assert len({s["common"]["n"] for s in long[1:]}) == 1
    copy = {k: v for k, v in report.items() if k != "study_id"}
    assert hashlib.sha256(study.encode(copy)).hexdigest() == report["study_id"]


def test_empty_errors_are_unavailable_not_zero():
    assert study.score([]) == {"n": 0, "mae": None, "rmse": None, "bias": None}
    assert study.score([{"prediction": 12, "truth": 10}]) == {
        "n": 1,
        "mae": 2,
        "rmse": 2,
        "bias": 2,
    }
