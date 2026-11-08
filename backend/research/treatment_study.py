"""Training-only missing-input reconstruction; no forecast model fitting or Neon writes."""

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import random
import statistics
import zipfile
from datetime import date, timedelta
from pathlib import Path

from app.api.preparation import encode

from research import release1 as r1

ROOT = Path(__file__).resolve().parents[2]
BUNDLE_SHA = "bbcf319b97029d15a8180849b3f7ca218ef1e3ef7debf4ed01d32c511516c81a"
SNAPSHOT_ID = "7d45aacb7d94c05410e3ac9e97ceba3a7734500d4a1881e4829e2d7fab70acf0"
SEED = 20261108
POLICIES = (
    "observed_only",
    "past_original_3",
    "seasonal_original_7",
    "weekday_median_28",
    "past_median_365",
)
PROTOCOL = {
    "version": "missing_input_treatment_v1",
    "metric": "energy_generated",
    "unit": "million_kWh",
    "start": "2020-01-01",
    "end": "2023-12-31",
    "snapshot_id": SNAPSHOT_ID,
    "source_bundle_sha256": BUNDLE_SHA,
    "seed": SEED,
    "block_days": [1, 3, 7, 14, 30],
    "requested_windows_per_length": 20,
    ("masks"): (
        "Original eligible continuous blocks within one training year, "
        "after 90 warm-up days and before final two training days; seeded "
        "per-year shuffles then round-robin years; 28-day separation within "
        "each length experiment."
    ),
    ("timing"): (
        "Masked input D reconstructed for hypothetical target D+2, issued "
        "noon Bangladesh D+1. All donors strictly before D; known late "
        "donors refused; unknown historical times assumed, not verified."
    ),
    "policies": {
        "observed_only": "Abstain; no invented zero error.",
        "past_original_3": "Most recent available original within D-1..D-3; no recursion.",
        "seasonal_original_7": "Exact available original D-7.",
        ("weekday_median_28"): (
            "Median of available original D-7,D-14,D-21,D-28; at least two donors."
        ),
        "past_median_365": "Median of original available values D-365..D-1; at least 30 donors.",
    },
    ("selection"): (
        "Provisional reconstruction candidate: minimum pooled common-date "
        "MAE across lengths 1 and 3 among four estimating policies, tie by "
        "policy ID. Report own coverage and errors separately. No automatic "
        "approval or model adoption."
    ),
    ("real_gap_candidates"): (
        "Only originally absent inputs, no review-held values; require a "
        "prior available original at most three calendar days earlier. No "
        "future endpoint or total-run length used for eligibility. "
        "Candidate feature inputs only; never training labels or scoring "
        "actuals."
    ),
    ("scope"): (
        "Training-only reconstruction study. No validation/test "
        "reconstruction, forecast evaluation, new forecast fitting, master "
        "changes or proof of the real missingness mechanism."
    ),
}


def csv_data(rows, fields=None):
    out = io.StringIO(newline="")
    fields = fields or list(rows[0]) if rows else fields or ["No rows"]
    w = csv.DictWriter(out, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
    return out.getvalue().encode("utf-8-sig")


def score(trials):
    errors = [x["prediction"] - x["truth"] for x in trials if x["prediction"] is not None]
    return {
        "n": len(errors),
        "mae": sum(abs(v) for v in errors) / len(errors) if errors else None,
        "rmse": math.sqrt(sum(v * v for v in errors) / len(errors)) if errors else None,
        "bias": sum(errors) / len(errors) if errors else None,
    }


def estimate(series, day, policy):
    if policy not in POLICIES:
        raise ValueError("Unknown treatment policy")
    if policy == "observed_only":
        return None
    offsets = (
        range(1, 4)
        if policy == "past_original_3"
        else (7,)
        if policy == "seasonal_original_7"
        else (7, 14, 21, 28)
        if policy == "weekday_median_28"
        else range(1, 366)
    )
    donors = []
    for offset in offsets:
        d = day - timedelta(days=offset)
        candidate = (
            r1.donor(series, d, day + timedelta(days=2))
            if series.get(d, {}).get("eligible")
            else None
        )
        if candidate:
            donors.append((d, candidate[0], candidate[2]))
            if policy in ("past_original_3", "seasonal_original_7"):
                break
    required = 2 if policy == "weekday_median_28" else 30 if policy == "past_median_365" else 1
    if len(donors) < required:
        return None
    value = statistics.median(v for _, v, _ in donors)
    evidence = [
        (str(d), series[d]["original"], series[d]["version_id"], series[d]["source_sha256"])
        for d, _, _ in donors
    ]
    return {
        "value": value,
        "donor_count": len(donors),
        "donor_first": str(min(d for d, _, _ in donors)),
        "donor_last": str(max(d for d, _, _ in donors)),
        "unknown_donor_times": sum(unknown for _, _, unknown in donors),
        "donor_fingerprint": hashlib.sha256(encode(sorted(evidence))).hexdigest(),
    }


def mask_windows(series, length):
    groups = {year: [] for year in range(2020, 2024)}
    for day in sorted(series):
        last = day + timedelta(days=length - 1)
        if (
            day < r1.START + timedelta(days=90)
            or last > r1.TRAIN_END - timedelta(days=2)
            or day.year != last.year
        ):
            continue
        if all(series.get(day + timedelta(days=i), {}).get("eligible") for i in range(length)):
            groups[day.year].append(day)
    for year, days in groups.items():
        random.Random(SEED + length * 100 + year).shuffle(days)
    selected, blocked = [], set()
    while any(groups.values()) and len(selected) < 20:
        for year in groups:
            while groups[year]:
                day = groups[year].pop()
                expanded = {day + timedelta(days=i) for i in range(-28, length + 28)}
                if {day + timedelta(days=i) for i in range(length)} & blocked:
                    continue
                selected.append([day + timedelta(days=i) for i in range(length)])
                blocked |= expanded
                break
            if len(selected) == 20:
                break
    return sorted(selected)


def gap_register(series, audit):
    records = []
    for a in audit:
        day = date.fromisoformat(a["operational_date"])
        if day not in series or series[day]["eligible"]:
            continue
        row = series[day]
        category = "review_held" if a["review_hold"] == "True" else a["state"]
        records.append(
            {
                "date": str(day),
                "category": category,
                "original_value": a["original_value"],
                "review_flags": a["review_flags"],
                "version_id": a["version_id"],
                "source_id": a["source_id"],
                "source_sha256": row["source_sha256"],
                "recovery_status": "not_assessed",
                "action": "Inspect original source/definition; no automatic correction"
                if category == "review_held"
                else (
                    "Investigate registered sources and archive; absent canonical data "
                    "is not proof of no official PDF"
                ),
            }
        )
    return records


def run(data):
    if hashlib.sha256(data).hexdigest() != BUNDLE_SHA:
        raise ValueError("Frozen input bytes differ from the declared study")
    manifest, full, coverage = r1.read_input(data)
    if manifest["snapshot_id"] != SNAPSHOT_ID:
        raise ValueError("Unexpected input snapshot")
    # Physically remove all validation/test rows before every treatment calculation.
    series = {d: dict(row) for d, row in full.items() if r1.START <= d <= r1.TRAIN_END}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        audit = list(
            csv.DictReader(io.StringIO(archive.read("daily_audit.csv").decode("utf-8-sig")))
        )
    register = gap_register(series, audit)
    calendar = [
        {
            "date": str(d),
            "original_value": row["original"],
            "eligible": row["eligible"],
            "version_id": row["version_id"],
            "source_sha256": row["source_sha256"],
            "available_at": row["available_at"],
        }
        for d, row in sorted(series.items())
    ]
    trials, windows = [], []
    for length in PROTOCOL["block_days"]:
        selected = mask_windows(series, length)
        if not selected:
            raise ValueError(f"No eligible training masks for length {length}")
        hidden = {d for block in selected for d in block}
        masked = {
            d: {**row, "value": None if d in hidden else row["value"]} for d, row in series.items()
        }
        for index, block in enumerate(selected, 1):
            windows.append(
                {
                    "block_days": length,
                    "window": index,
                    "start": str(block[0]),
                    "end": str(block[-1]),
                    "days": len(block),
                }
            )
            for day in block:
                for policy in POLICIES:
                    candidate = estimate(masked, day, policy)
                    trials.append(
                        {
                            "block_days": length,
                            "window": index,
                            "date": str(day),
                            "policy": policy,
                            "truth": series[day]["value"],
                            "prediction": candidate["value"] if candidate else None,
                            "donor_count": candidate["donor_count"] if candidate else 0,
                            "donor_first": candidate["donor_first"] if candidate else None,
                            "donor_last": candidate["donor_last"] if candidate else None,
                            "unknown_donor_times": candidate["unknown_donor_times"]
                            if candidate
                            else 0,
                            "donor_fingerprint": candidate["donor_fingerprint"]
                            if candidate
                            else None,
                        }
                    )
    summaries = []
    for length in PROTOCOL["block_days"]:
        subset = [t for t in trials if t["block_days"] == length]
        common = set.intersection(
            *(
                {t["date"] for t in subset if t["policy"] == p and t["prediction"] is not None}
                for p in POLICIES[1:]
            )
        )
        count = sum(t["policy"] == POLICIES[0] for t in subset)
        for policy in POLICIES:
            own = [t for t in subset if t["policy"] == policy]
            filled = [t for t in own if t["prediction"] is not None]
            summaries.append(
                {
                    "block_days": length,
                    "policy": policy,
                    "windows": sum(w["block_days"] == length for w in windows),
                    "masked_days": count,
                    "filled_days": len(filled),
                    "coverage_percent": 100 * len(filled) / count if count else None,
                    "known_time_fillable_days": sum(t["unknown_donor_times"] == 0 for t in filled),
                    "conditional": score(filled),
                    "common": score([t for t in filled if t["date"] in common]),
                }
            )
    # A date can occur in BOTH length experiments: keep (length,date) identities for pooling.
    identities = {}
    for length in (1, 3):
        identities[length] = set.intersection(
            *(
                {
                    t["date"]
                    for t in trials
                    if t["block_days"] == length
                    and t["policy"] == p
                    and t["prediction"] is not None
                }
                for p in POLICIES[1:]
            )
        )
    ranking = []
    for p in POLICIES[1:]:
        selected = [
            t
            for t in trials
            if t["block_days"] in (1, 3)
            and t["policy"] == p
            and t["date"] in identities[t["block_days"]]
        ]
        ranking.append({"policy": p, **score(selected)})
    ranking.sort(key=lambda r: (r["mae"] if r["mae"] is not None else math.inf, r["policy"]))
    candidates = []
    for row in register:
        day = date.fromisoformat(row["date"])
        previous = next(
            (
                day - timedelta(days=i)
                for i in range(1, 4)
                if series.get(day - timedelta(days=i), {}).get("eligible")
                and r1.donor(series, day - timedelta(days=i), day + timedelta(days=2))
            ),
            None,
        )
        allowed = series[day]["original"] is None and previous is not None
        for policy in POLICIES[1:]:
            value = estimate(series, day, policy) if allowed else None
            candidates.append(
                {
                    "date": str(day),
                    "policy": policy,
                    "original_value": series[day]["original"],
                    "candidate_input_value": value["value"] if value else None,
                    "status": "unapproved_feature_input_candidate" if value else "withheld",
                    "reason": "past_only_candidate_not_a_label"
                    if value
                    else "held_or_no_original_in_prior_three_days_or_insufficient_donors",
                    **({k: v for k, v in value.items() if k != "value"} if value else {}),
                }
            )
    exports = {
        "training_calendar": csv_data(calendar),
        "masked_windows": csv_data(windows),
        "masked_trials": csv_data(trials),
        "input_candidates": csv_data(
            candidates, list(dict.fromkeys(k for row in candidates for k in row))
        ),
    }
    flat = [
        {
            **{k: v for k, v in row.items() if k not in ("conditional", "common")},
            **{"conditional_" + k: v for k, v in row["conditional"].items()},
            **{"common_" + k: v for k, v in row["common"].items()},
        }
        for row in summaries
    ]
    exports["summary"] = csv_data(flat)
    report = {
        "protocol": PROTOCOL,
        "code_sha256": {
            p.name: hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
            for p in (Path(__file__), Path(r1.__file__))
        },
        "training_coverage": {year: row for year, row in coverage.items() if int(year) <= 2023},
        "register": register,
        "summaries": summaries,
        "short_gap_ranking": ranking,
        "provisional_candidate": ranking[0]["policy"] if ranking and ranking[0]["n"] else None,
        "actual_candidate_summary": {
            p: sum(c["policy"] == p and c["candidate_input_value"] is not None for c in candidates)
            for p in POLICIES[1:]
        },
        "checks": {
            "training_days": len(series),
            "eligible_originals": sum(r["eligible"] for r in series.values()),
            "validation_test_rows_used": 0,
            "forecast_models_trained": 0,
            "database_writes": 0,
            "all_donors_strictly_past": all(
                t["donor_last"] is None or t["donor_last"] < t["date"] for t in trials
            ),
            "all_masks_eligible_training_originals": all(
                date.fromisoformat(t["date"]) in series
                and series[date.fromisoformat(t["date"])]["eligible"]
                for t in trials
            ),
            "requested_windows_per_length": 20,
            "masked_windows": windows,
        },
        "exports": {
            k: {"bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()}
            for k, v in exports.items()
        },
        "limitations": [
            "Missingness causes are not inferred from an absent canonical value.",
            (
                "Artificial complete-block masks are not the real missingness "
                "mechanism; selection favors eligible continuous stretches."
            ),
            (
                "Unknown historical publication times are assumed; platform "
                "reconstruction is not verified real-time availability."
            ),
            (
                "Conditional errors use different samples. Common-date comparisons "
                "and coverage must be interpreted together."
            ),
            (
                "A reconstruction candidate is not an approved imputer or evidence "
                "of improved downstream forecasts."
            ),
            (
                "No held/missing target was filled. Existing models and the already "
                "evaluated 2025 results are unchanged."
            ),
            (
                "This study is energy-specific, not authorization to create "
                "historical temperature/cost values."
            ),
        ],
    }
    report["study_id"] = hashlib.sha256(encode(report)).hexdigest()
    return report, exports


def markdown(r):
    lines = [
        "# Missing-Data Treatment Study",
        "",
        f"Study ID: {r['study_id']}",
        "",
        (
            "Training-only energy input reconstruction, 2020-2023. No forecast "
            "retraining or master-data modification."
        ),
        "",
        (
            "| Gap days | Policy | Windows | Masked | Filled | Coverage % | "
            "Conditional MAE | Common n | Common MAE |"
        ),
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    def f(v):
        return "unavailable" if v is None else f"{v:.4f}"

    for s in r["summaries"]:
        lines.append(
            f"| {s['block_days']} | {s['policy']} | {s['windows']} | {s['masked_days']} "
            f"| {s['filled_days']} | {f(s['coverage_percent'])} "
            f"| {f(s['conditional']['mae'])} | {s['common']['n']} "
            f"| {f(s['common']['mae'])} |"
        )
    lines += [
        "",
        f"Provisional short-gap reconstruction candidate: {r['provisional_candidate']}. "
        "Not automatically approved for model inputs.",
        "",
        "## Limitations",
        "",
    ] + [f"- {v}" for v in r["limitations"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--online", action="store_true")
    group.add_argument("--bundle", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/treatment_study")
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    service = None
    try:
        if args.online:
            from ingestion.drive_sync import digest, download, find_files
            from ingestion.online_recovery import drive_service

            service, folder = drive_service()
            found = find_files(service, folder, "blob", BUNDLE_SHA)
            if len(found) != 1:
                raise ValueError("Exact frozen input unavailable")
            path = output / "frozen_input.zip"
            download(service, found[0]["id"], path)
            if digest(path) != BUNDLE_SHA:
                raise ValueError("Source bytes differ")
            data = path.read_bytes()
        else:
            data = args.bundle.read_bytes()
        report, exports = run(data)
        files = {
            "study.json": encode(report),
            "study.json.gz": gzip.compress(encode(report), mtime=0),
            "study_report.md": markdown(report).encode(),
        }
        for name, value in exports.items():
            files[name + ".csv"] = value
            files[name + ".csv.gz"] = gzip.compress(value, mtime=0)
        for name, value in files.items():
            (output / name).write_bytes(value)
        manifest = {
            "study_id": report["study_id"],
            "files": {
                k: {"bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()}
                for k, v in files.items()
            },
        }
        (output / "manifest.json").write_bytes(encode(manifest))
        if service:
            from ingestion.drive_sync import upload_blob

            receipt = {
                name: upload_blob(service, folder, output / name)
                for name in (*files, "manifest.json")
            }
            (output / "storage_receipt.json").write_bytes(encode(receipt))
            upload_blob(service, folder, output / "storage_receipt.json")
        print(
            json.dumps(
                {
                    "status": "completed",
                    "study_id": report["study_id"],
                    "short_gap_ranking": report["short_gap_ranking"],
                    "checks": {k: v for k, v in report["checks"].items() if k != "masked_windows"},
                    "drive_archived": bool(service),
                },
                indent=2,
            )
        )
    finally:
        if service:
            service.close()


if __name__ == "__main__":
    main()
