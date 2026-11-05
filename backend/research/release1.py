"""Release 1: frozen data, train-only experiments and reserved-test forecasting.

Run --online in the hosted worker, or --bundle with its preserved input.
No final-test predictions, labels, features or metrics are exported as results.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import platform
import random
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

from app.api.preparation import bundle, encode, read_snapshot

ROOT = Path(__file__).resolve().parents[2]
START, TRAIN_END, VAL_END, END = map(
    date.fromisoformat, ("2020-01-01", "2023-12-31", "2024-12-31", "2025-12-31")
)
POLICIES = ("complete", "past_original_3", "seasonal_original_7")
ALPHAS = (0.1, 1.0, 10.0, 100.0)
FEATURES = (
    "lag_2",
    "lag_7",
    "lag_14",
    "lag_28",
    "mean_2_to_8",
    "mean_2_to_29",
    "weekday_sin",
    "weekday_cos",
    "year_sin",
    "year_cos",
)
SEED = 20261105
PROTOCOL = {
    "version": "release1_v1",
    "target": "energy_generated",
    "unit": "million_kWh",
    "start": str(START),
    "training_end": str(TRAIN_END),
    "validation_end": str(VAL_END),
    "reserved_test_end": str(END),
    "reserved_test_year": 2025,
    "forecast_issue": "12:00 Asia/Dhaka on the day before target date",
    "reporting_scenario": "Original day D assumed available at noon D+1; unknown times assumed",
    "latest_input_lag_days": 2,
    "features": FEATURES,
    "ridge_alphas": ALPHAS,
    "policies": POLICIES,
    "seed": SEED,
    "training_cv": "2021, 2022, 2023 full-year expanding-origin folds; fixed fit per fold",
    "selection": (
        "Lowest pooled training-fold common-date MAE; deterministic policy/alpha tie break"
    ),
    "validation": "Locked selected configuration, fit through 2023-12-30, no validation tuning",
    "minimum_common_training_fold_dates": 10,
}


def read_input(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for name, spec in manifest["files"].items():
            value = archive.read(name)
            if len(value) != spec["bytes"] or hashlib.sha256(value).hexdigest() != spec["sha256"]:
                raise ValueError("Input file checksum mismatch")
        original = json.loads(archive.read("original_snapshot.json"))
        audit = list(
            csv.DictReader(io.StringIO(archive.read("daily_audit.csv").decode("utf-8-sig")))
        )
    if (
        hashlib.sha256(encode({"config": manifest["config"], "original": original})).hexdigest()
        != manifest["snapshot_id"]
    ):
        raise ValueError("Snapshot identity mismatch")
    config = manifest["config"]
    for key, expected in {
        "start_date": str(START),
        "end_date": str(END),
        "train_end": str(TRAIN_END),
        "validation_end": str(VAL_END),
        "metric": "energy_generated",
        "policy": "observed_only",
    }.items():
        if config[key] != expected:
            raise ValueError("Experiment protocol does not match frozen input")
    expected_dates = [str(START + timedelta(days=i)) for i in range((END - START).days + 1)]
    if [r["operational_date"] for r in audit] != expected_dates:
        raise ValueError("Calendar gaps must be retained as rows")
    by_date = {d["operational_date"]: d for d in original}
    if len(by_date) != len(original):
        raise ValueError("Duplicate original dates")
    series = {}
    coverage = {}
    for row in audit:
        day = date.fromisoformat(row["operational_date"])
        expected_split = "train" if day <= TRAIN_END else "validation" if day <= VAL_END else "test"
        d = by_date.get(str(day))
        matches = [m for m in d["measurements"] if m["metric"] == "energy_generated"] if d else []
        if len(matches) > 1:
            raise ValueError("Duplicate energy observations")
        m = matches[0] if matches else None
        if row["split"] != expected_split or row["original_value"] != (
            (m["value"] or "") if m else ""
        ):
            raise ValueError("Audit/original or chronological split mismatch")
        eligible = row["observed_target_candidate"] == "True"
        if eligible and (
            m is None
            or m["value"] is None
            or not math.isfinite(float(m["value"]))
            or float(m["value"]) <= 0
        ):
            raise ValueError("Invalid eligible energy")
        year = coverage.setdefault(
            str(day.year), {"calendar": 0, "observed": 0, "eligible": 0, "held": 0}
        )
        year["calendar"] += 1
        year["observed"] += bool(row["original_value"])
        year["eligible"] += eligible
        year["held"] += row["review_hold"] == "True"
        # Reserve test labels from ALL modelling and feature construction.
        if day > VAL_END:
            continue
        source = (
            next((s for s in d["sources"] if m and s["id"] == m["source_id"]), None) if d else None
        )
        if m and (
            (m["unit"], m["period"], m["zone"], m["fuel"])
            != ("million_kWh", "daily", "national", None)
            or source is None
        ):
            raise ValueError("Energy dimensions or source lineage mismatch")
        series[day] = {
            "value": float(m["value"]) if eligible else None,
            "original": m["value"] if m else None,
            "eligible": eligible,
            "available_at": d["available_at"] if d else None,
            "version_id": d["report_version_id"] if d else None,
            "source_sha256": source["sha256"] if source else None,
        }
    return manifest, series, coverage


def cutoff(target):
    # Noon Bangladesh = 06:00 UTC, one calendar day before the target.
    return datetime.combine(target - timedelta(days=1), time(6), tzinfo=timezone.utc)


def donor(series, day, target, strict=False):
    row = series.get(day)
    if day > target - timedelta(days=2) or not row or row["value"] is None:
        return None
    available = row["available_at"]
    if available:
        when = datetime.fromisoformat(available.replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when > cutoff(target):
            return None
    elif strict:
        return None
    return row["value"], day, available is None


def input_value(series, requested, target, policy, strict=False):
    value = donor(series, requested, target, strict)
    if value:
        return value, False
    offsets = (
        range(1, 4)
        if policy == "past_original_3"
        else (7,)
        if policy == "seasonal_original_7"
        else ()
    )
    for offset in offsets:
        value = donor(series, requested - timedelta(days=offset), target, strict)
        if value:
            return value, True
    return None, False


def feature_row(series, target, policy, strict=False):
    inputs, sources, estimated = {}, [], 0
    for lag in (2, 7, 14, 28, *range(2, 30)):
        if lag in inputs:
            continue
        value, replaced = input_value(series, target - timedelta(days=lag), target, policy, strict)
        if value is None:
            return None
        inputs[lag] = value[0]
        sources.append(value)
        estimated += replaced
    angle = 2 * math.pi * ((target - date(target.year, 1, 1)).days) / 365.25
    weekday = 2 * math.pi * target.weekday() / 7
    values = [inputs[i] for i in (2, 7, 14, 28)]
    values += [sum(inputs[i] for i in range(2, 9)) / 7, sum(inputs[i] for i in range(2, 30)) / 28]
    values += [math.sin(weekday), math.cos(weekday), math.sin(angle), math.cos(angle)]
    return {
        "x": values,
        "latest_donor": str(max(v[1] for v in sources)),
        "unknown_availability_inputs": sum(v[2] for v in sources),
        "replaced_inputs": estimated,
    }


def metrics(truth, predictions):
    errors = [p - y for y, p in zip(truth, predictions, strict=True)]
    if not errors:
        return {"n": 0, "mae": None, "rmse": None, "bias": None}
    return {
        "n": len(errors),
        "mae": sum(abs(e) for e in errors) / len(errors),
        "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)),
        "bias": sum(errors) / len(errors),
    }


def fit(series, policy, alpha, stop):
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    samples = [
        (d, feature_row(series, d, policy))
        for d in sorted(series)
        if d <= stop and series[d]["eligible"] and donor(series, d, stop + timedelta(days=2))
    ]
    samples = [(d, f) for d, f in samples if f]
    if len(samples) < 60:
        raise ValueError("Insufficient eligible training rows for protocol")
    model = make_pipeline(StandardScaler(), Ridge(alpha=alpha, solver="svd"))
    model.fit([f["x"] for _, f in samples], [series[d]["value"] for d, _ in samples])
    return model, {"rows": len(samples), "last_label": str(max(d for d, _ in samples))}


def evaluate(model, series, policy, dates):
    usable = []
    for day in dates:
        f = feature_row(series, day, policy)
        if f:
            usable.append((day, f))
    if not usable:
        return {}
    values = model.predict([f["x"] for _, f in usable])
    return {day: float(value) for (day, _), value in zip(usable, values, strict=True)}


def training_cv(series):
    folds = []
    candidates = {(p, a): {} for p in POLICIES for a in ALPHAS}
    for year in (2021, 2022, 2023):
        first, last = date(year, 1, 1), date(year, 12, 31)
        dates = [d for d in sorted(series) if first <= d <= last and series[d]["eligible"]]
        predictions = {}
        for p, a in candidates:
            model, fit_info = fit(series, p, a, first - timedelta(days=2))
            predictions[p, a] = evaluate(model, series, p, dates)
            if date.fromisoformat(fit_info["last_label"]) > first - timedelta(days=2):
                raise ValueError("Training label crosses forecast origin")
        common = sorted(set.intersection(*(set(v) for v in predictions.values())))
        if len(common) < 10:
            raise ValueError("Insufficient common dates in a training fold")
        folds.append(
            {
                "start": str(first),
                "end": str(last),
                "common_dates": len(common),
                "latest_fit_label": str(first - timedelta(days=2)),
            }
        )
        for key, predicted in predictions.items():
            candidates[key].update({d: predicted[d] for d in common})
    scores = []
    for (p, a), predicted in candidates.items():
        days = sorted(predicted)
        scores.append(
            {
                "policy": p,
                "alpha": a,
                **metrics([series[d]["value"] for d in days], [predicted[d] for d in days]),
            }
        )
    scores.sort(key=lambda r: (r["mae"], r["policy"], r["alpha"]))
    return scores[0], scores, folds


def masking_experiment(series):
    output = []
    for length in (1, 3, 7):
        candidates = [
            d
            for d in sorted(series)
            if d <= TRAIN_END - timedelta(days=length - 1)
            and all(series.get(d + timedelta(days=i), {}).get("eligible") for i in range(length))
        ]
        random.Random(SEED + length).shuffle(candidates)
        blocked, windows = set(), []
        for first in candidates:
            expanded = {first + timedelta(days=i) for i in range(-7, length + 7)}
            if blocked & expanded:
                continue
            windows.append([first + timedelta(days=i) for i in range(length)])
            blocked |= expanded
            if len(windows) == 20:
                break
        hidden = {d for window in windows for d in window}
        masked = {
            d: {**r, "value": None if d in hidden else r["value"]}
            for d, r in series.items()
            if d <= TRAIN_END
        }
        predictions = {}
        for policy in POLICIES:
            predictions[policy] = {}
            for day in sorted(hidden):
                value, _ = input_value(masked, day, day + timedelta(days=2), policy)
                if value:
                    predictions[policy][day] = value[0]
        common = set(predictions[POLICIES[1]]) & set(predictions[POLICIES[2]])
        for policy, values in predictions.items():
            days = sorted(values)
            comparable = sorted(common & set(values))
            output.append(
                {
                    "block_days": length,
                    "windows": len(windows),
                    "policy": policy,
                    "masked_days": len(hidden),
                    "filled_days": len(days),
                    "coverage_percent": 100 * len(days) / len(hidden) if hidden else 0,
                    "conditional": metrics(
                        [series[d]["value"] for d in days], [values[d] for d in days]
                    ),
                    "common": metrics(
                        [series[d]["value"] for d in comparable], [values[d] for d in comparable]
                    ),
                }
            )
    return output


def run(data, readiness=None):
    manifest, series, coverage = read_input(data)
    winner, cv, folds = training_cv(series)
    model, fit_info = fit(series, winner["policy"], winner["alpha"], TRAIN_END - timedelta(days=1))
    dates = [d for d in sorted(series) if d > TRAIN_END]
    ridge = evaluate(model, series, winner["policy"], dates)
    predictions = []
    for day in dates:
        latest, weekly = (
            donor(series, day - timedelta(days=2), day),
            donor(series, day - timedelta(days=7), day),
        )
        f = feature_row(series, day, winner["policy"])
        predictions.append(
            {
                "date": str(day),
                "actual": series[day]["value"],
                "original_actual": series[day]["original"],
                "eligible_target": series[day]["eligible"],
                "latest_report": latest[0] if latest else None,
                "weekly": weekly[0] if weekly else None,
                "ridge": ridge.get(day),
                "latest_donor": f["latest_donor"] if f else None,
                "unknown_availability_inputs": f["unknown_availability_inputs"] if f else None,
                "replaced_inputs": f["replaced_inputs"] if f else None,
            }
        )
    common = [
        r
        for r in predictions
        if r["actual"] is not None
        and all(r[k] is not None for k in ("latest_report", "weekly", "ridge"))
    ]
    validation = []
    for name in ("latest_report", "weekly", "ridge"):
        own = [r for r in predictions if r["actual"] is not None and r[name] is not None]
        validation.append(
            {
                "model": name,
                "calendar_forecasts": sum(r[name] is not None for r in predictions),
                "own_dates": metrics([r["actual"] for r in own], [r[name] for r in own]),
                "common_dates": metrics([r["actual"] for r in common], [r[name] for r in common]),
            }
        )
    strict_features = sum(
        feature_row(series, d, winner["policy"], strict=True) is not None for d in dates
    )
    scaler, ridge_model = model.steps[0][1], model.steps[1][1]
    fitted = {
        "feature_names": FEATURES,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coefficients": ridge_model.coef_.tolist(),
        "intercept": float(ridge_model.intercept_),
        "policy": winner["policy"],
        "alpha": winner["alpha"],
        **fit_info,
    }
    import numpy as np

    model_check = max(
        (
            abs(
                float(model.predict([feature_row(series, d, winner["policy"])["x"]])[0])
                - predict_saved(fitted, feature_row(series, d, winner["policy"])["x"])
            )
            for d in ridge
        ),
        default=0,
    )
    if model_check > 1e-8:
        raise ValueError("Saved model inference mismatch")
    source_hash = hashlib.sha256(Path(__file__).read_text(encoding="utf-8").encode()).hexdigest()
    report = {
        "release": "Release 1",
        "protocol": PROTOCOL,
        "snapshot_id": manifest["snapshot_id"],
        "source_bundle_sha256": hashlib.sha256(data).hexdigest(),
        "code_sha256": source_hash,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "sklearn": version("scikit-learn"),
        },
        "coverage": coverage,
        "full_history_readiness": readiness,
        "selected": winner,
        "training_cv": cv,
        "folds": folds,
        "masking": masking_experiment(series),
        "validation": validation,
        "predictions": predictions,
        "model": fitted,
        "strict_availability_feature_days": strict_features,
        "reserved_test": {
            "year": 2025,
            "status": "not_evaluated",
            "metrics": None,
            "predictions": None,
        },
        "test_report": {
            "calendar_verified": True,
            "no_test_labels_in_series": max(series) <= VAL_END,
            "no_test_predictions": all(r["date"] <= str(VAL_END) for r in predictions),
            "training_selection_only": True,
            "saved_model_max_difference": model_check,
            "neon_writes": 0,
            "validation_calendar_days": len(dates),
            "common_validation_days": len(common),
        },
        "limitations": [
            "Retrospective reporting-delay scenario using current canonical "
            "revisions, not a verified point-in-time backtest.",
            "Unknown publication times are assumed; known late sources are "
            "excluded. Strict availability coverage is reported separately.",
            "Lag 2 is the latest report scenario, not a claim that "
            "target-day-minus-one energy is available at issue time.",
            "Validation 2024 has previously been explored descriptively. Final "
            "test 2025 is not evaluated in this release.",
            "Artificial training masks assess reconstruction, not the true "
            "missingness mechanism or operational accuracy.",
            "Errors conditional on successful forecasts require coverage and "
            "common-date comparison.",
            "Model predictions are research outputs; they never replace "
            "original measurements or missing evaluation targets.",
        ],
    }
    report["experiment_id"] = hashlib.sha256(
        encode(
            {
                k: v
                for k, v in report.items()
                if k not in ("full_history_readiness", "source_bundle_sha256")
            }
        )
    ).hexdigest()
    return report, series


def predict_saved(model, features):
    return model["intercept"] + sum(
        (x - m) / s * c
        for x, m, s, c in zip(
            features, model["mean"], model["scale"], model["coefficients"], strict=True
        )
    )


def csv_bytes(rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")


def test_markdown(report):
    selected = report["selected"]
    lines = [
        "# Release 1 execution and test report",
        "",
        "## Experiment scope",
        "",
        "Target: next-day national energy generation, million kWh. Training 2020–2023; "
        "validation 2024; final test 2025 reserved and not evaluated.",
        "",
        "Retrospective reporting-delay scenario: issue at noon Bangladesh on T-1; "
        "latest original input T-2. Unknown historical publication times are assumed, "
        "not verified. These results do not establish live forecasting accuracy.",
        "",
        f"Snapshot: `{report['snapshot_id']}`",
        "",
        f"Experiment: `{report['experiment_id']}`",
        "",
        f"Training-fold selection: {selected['policy']}, Ridge alpha={selected['alpha']}.",
        "",
        "## Validation results — identical common dates",
        "",
        "| Model | Dates | MAE | RMSE | Bias | Own scored dates | Calendar forecasts |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["validation"]:
        m = row["common_dates"]
        lines.append(
            f"| {row['model']} | {m['n']} | {m['mae']} | {m['rmse']} | "
            f"{m['bias']} | {row['own_dates']['n']} | {row['calendar_forecasts']} |"
        )
    lines += ["", "## Executed pipeline checks", ""]
    lines += [f"- {key}: {value}" for key, value in report["test_report"].items()]
    lines += [
        f"- Strict publication-time feature coverage: "
        f"{report['strict_availability_feature_days']}/366 validation days.",
        "",
        "These are pipeline acceptance checks. Automated unit/CI test counts are recorded "
        "separately in the release notes; they are not inferred from model scores.",
        "",
        "## Limitations",
        "",
    ]
    lines += ["- " + text for text in report["limitations"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/experiments/release1")
    args = parser.parse_args()
    if bool(args.online) == bool(args.bundle):
        parser.error("Choose exactly one of --online or --bundle")
    readiness = None
    if args.online:
        from app.api.monitoring import read_session
        from app.api.quality import read_quality

        with contextmanager(read_session)() as session:
            readiness = read_quality(session).model_dump(mode="json")
            snapshot = read_snapshot(session, "energy_generated", START, END, TRAIN_END, VAL_END)
        data = bundle(snapshot)
    else:
        data = args.bundle.read_bytes()
    report, series = run(data, readiness)
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "frozen_input.zip": data,
        "experiment.json": encode(report),
        "experiment.json.gz": gzip.compress(encode(report), mtime=0),
        "model.json": encode(report["model"]),
        "validation_predictions.csv": csv_bytes(report["predictions"]),
        "training_selection.csv": csv_bytes(report["training_cv"]),
        "test_report.md": test_markdown(report).encode("utf-8"),
    }
    feature_rows = []
    for day in sorted(series):
        f = feature_row(series, day, report["selected"]["policy"])
        feature_rows.append(
            {
                "date": str(day),
                "split": "train" if day <= TRAIN_END else "validation",
                "original_target": series[day]["original"],
                "eligible_target": series[day]["eligible"],
                **dict(zip(FEATURES, f["x"] if f else [None] * len(FEATURES), strict=True)),
                "latest_donor": f["latest_donor"] if f else None,
            }
        )
    files["features_train_validation.csv"] = csv_bytes(feature_rows)
    for name, value in files.items():
        (output / name).write_bytes(value)
    manifest = {
        "experiment_id": report["experiment_id"],
        "snapshot_id": report["snapshot_id"],
        "files": {
            n: {"bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()} for n, v in files.items()
        },
    }
    (output / "manifest.json").write_bytes(encode(manifest))
    if args.online:
        from ingestion.drive_sync import upload_blob
        from ingestion.online_recovery import drive_service

        service, folder = drive_service()
        try:
            receipt = {
                n: upload_blob(service, folder, output / n) for n in (*files, "manifest.json")
            }
            (output / "storage_receipt.json").write_bytes(encode(receipt))
            upload_blob(service, folder, output / "storage_receipt.json")
        finally:
            service.close()
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "experiment_id",
                    "snapshot_id",
                    "selected",
                    "validation",
                    "test_report",
                    "strict_availability_feature_days",
                )
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
