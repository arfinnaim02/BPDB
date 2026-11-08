import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Independently verify exported treatment evidence; no database or model fitting."
)
parser.add_argument("--folder", type=Path, required=True)
parser.add_argument("--compare", type=Path, help="Optional independent rerun directory")
args = parser.parse_args()
out = args.folder
r = json.loads((out / "study.json").read_bytes())
m = json.loads((out / "manifest.json").read_bytes())
receipt = (
    json.loads((out / "storage_receipt.json").read_bytes())
    if (out / "storage_receipt.json").exists()
    else {}
)
for n, i in m["files"].items():
    b = (out / n).read_bytes()
    assert len(b) == i["bytes"] and hashlib.sha256(b).hexdigest() == i["sha256"]
    if receipt:
        assert receipt[n]["sha256"] == i["sha256"] and receipt[n]["size"] == i["bytes"]
    if args.compare:
        local = (args.compare / n).read_bytes()
        assert (gzip.decompress(b) == gzip.decompress(local)) if n.endswith(".gz") else b == local
if receipt:
    assert (
        receipt["manifest.json"]["sha256"]
        == hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest()
    )


def read(n):
    return list(csv.DictReader(io.StringIO((out / (n + ".csv")).read_bytes().decode("utf-8-sig"))))


calendar = {date.fromisoformat(x["date"]): x for x in read("training_calendar")}
windows = read("masked_windows")
trials = read("masked_trials")
proposals = read("input_candidates")
hidden = {
    n: {date.fromisoformat(x["date"]) for x in trials if x["block_days"] == n}
    for n in ["1", "3", "7", "14", "30"]
}
checks = 0
for row in trials:
    day = date.fromisoformat(row["date"])
    p = row["policy"]
    length = row["block_days"]
    assert day.year <= 2023 and calendar[day]["eligible"] == "True"
    assert float(row["truth"]) == float(calendar[day]["original_value"])
    offsets = {
        "observed_only": [],
        "past_original_3": range(1, 4),
        "seasonal_original_7": [7],
        "weekday_median_28": [7, 14, 21, 28],
        "past_median_365": range(1, 366),
    }[p]
    donors = []
    unknown = 0
    for k in offsets:
        d = day - timedelta(days=k)
        v = calendar.get(d)
        if d in hidden[length] or not v or v["eligible"] != "True":
            continue
        if v["available_at"]:
            when = datetime.fromisoformat(v["available_at"].replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            cutoff = datetime.combine(
                day + timedelta(days=1), datetime.min.time(), timezone.utc
            ) + timedelta(hours=6)
            if when > cutoff:
                continue
        donors.append((d, v))
        if p in ["past_original_3", "seasonal_original_7"]:
            break
    required = 2 if p == "weekday_median_28" else 30 if p == "past_median_365" else 1
    pred = (
        statistics.median(float(v["original_value"]) for _, v in donors)
        if len(donors) >= required
        else None
    )
    assert (pred is None and row["prediction"] == "") or abs(
        pred - float(row["prediction"])
    ) < 1e-10
    if pred is not None:
        assert int(row["donor_count"]) == len(donors)
        assert row["donor_last"] == str(max(d for d, _ in donors))
        assert int(row["unknown_donor_times"]) == sum(not v["available_at"] for _, v in donors)
        evidence = sorted(
            (str(d), v["original_value"], v["version_id"], v["source_sha256"] or None)
            for d, v in donors
        )
        encoded = json.dumps(
            evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        assert hashlib.sha256(encoded).hexdigest() == row["donor_fingerprint"]
    checks += 1
for s in r["summaries"]:
    own = [
        x
        for x in trials
        if int(x["block_days"]) == s["block_days"]
        and x["policy"] == s["policy"]
        and x["prediction"]
    ]
    assert len(own) == s["filled_days"]
    assert abs(s["coverage_percent"] - 100 * len(own) / s["masked_days"]) < 1e-10
    if own:
        e = [float(x["prediction"]) - float(x["truth"]) for x in own]
        assert abs(sum(map(abs, e)) / len(e) - s["conditional"]["mae"]) < 1e-10
        assert abs(math.sqrt(sum(v * v for v in e) / len(e)) - s["conditional"]["rmse"]) < 1e-10
        assert abs(sum(e) / len(e) - s["conditional"]["bias"]) < 1e-10
    else:
        assert s["conditional"]["mae"] is None
held = {x["date"] for x in r["register"] if x["category"] == "review_held"}
assert all(not x["candidate_input_value"] for x in proposals if x["date"] in held)
assert all(not x["original_value"] for x in proposals if x["candidate_input_value"])
verification = {
    "status": "passed",
    "study_id": r["study_id"],
    "independently_reconstructed_trials": checks,
    "manifest_files_verified": len(m["files"]),
    "drive_receipts_verified": len(receipt),
    "windows_by_length": {n: sum(x["block_days"] == n for x in windows) for n in hidden},
    "held_proposals_refused": len(held),
    "cross_platform_uncompressed_outputs_identical": True if args.compare else None,
    "compressed_bytes_note": (
        "Python/platform gzip headers may differ; hosted bytes checked against hosted manifest. "
        "Compare decompressed outputs when checking an independent rerun."
    ),
}
(out / "independent_verification.json").write_text(json.dumps(verification, indent=2))
print(json.dumps(verification, indent=2))
