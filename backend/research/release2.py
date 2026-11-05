"""Release 2: predefined model-family comparison on the exact Release 1 input."""

import argparse
import gzip
import hashlib
import json
import platform
import struct
from datetime import date, timedelta
from importlib.metadata import version
from pathlib import Path

from app.api.preparation import encode

from research import release1 as r1

ROOT = Path(__file__).resolve().parents[2]
BUNDLE_SHA = "bbcf319b97029d15a8180849b3f7ca218ef1e3ef7debf4ed01d32c511516c81a"
SNAPSHOT_ID = "7d45aacb7d94c05410e3ac9e97ceba3a7734500d4a1881e4829e2d7fab70acf0"
REFERENCE_ID = "fb42fc543c5b412475ad085dd14a028da3629e0e6085172e20945118f50ad76c"
POLICY = "seasonal_original_7"
SEED = 20261105
MODELS = (
    "latest_report",
    "weekly",
    "ridge",
    "autoregression",
    "random_forest",
    "gradient_boosting",
)
CANDIDATES = (
    {"family": "autoregression", "id": "ols", "parameters": {}},
    *(
        {
            "family": "random_forest",
            "id": f"rf_depth_{depth}",
            "parameters": {
                "n_estimators": 120,
                "max_depth": depth,
                "min_samples_leaf": 10,
                "max_features": 1.0,
                "bootstrap": True,
                "n_jobs": 1,
                "random_state": SEED,
            },
        }
        for depth in (4, 8)
    ),
    *(
        {
            "family": "gradient_boosting",
            "id": f"gb_depth_{depth}",
            "parameters": {
                "n_estimators": 150,
                "max_depth": depth,
                "min_samples_leaf": 10,
                "learning_rate": 0.03,
                "subsample": 1.0,
                "loss": "squared_error",
                "random_state": SEED,
            },
        }
        for depth in (2, 3)
    ),
)
PROTOCOL = {
    "version": "release2_v1",
    "target": "energy_generated",
    "unit": "million_kWh",
    "snapshot_id": SNAPSHOT_ID,
    "source_bundle_sha256": BUNDLE_SHA,
    "reference_experiment_id": REFERENCE_ID,
    "training": "2020-2023; three fixed-fit expanding origins at 2021, 2022, 2023",
    "validation": "2024; no tuning or model choice from validation outcomes",
    "test": "2025 reserved; no labels in modelling series, no predictions or metrics",
    "input_policy": POLICY,
    "features": r1.FEATURES,
    "timing": r1.PROTOCOL["reporting_scenario"],
    "issue": r1.PROTOCOL["forecast_issue"],
    "latest_input_lag_days": 2,
    "candidates": CANDIDATES,
    "training_scoring": "Identical Release 1 complete-feature dates within each training fold",
    "selection": "Per-family minimum pooled training-fold MAE, tie by configuration ID",
    "finalist": "Lowest pooled training-fold MAE among locked Ridge and three selected families",
    "validation_scoring": (
        "All six methods on identical observed target dates; own coverage separate"
    ),
    "refit": "Once through 2023-12-30, fixed coefficients/trees throughout validation",
    "minimum_training_rows": 60,
    "minimum_common_fold_dates": 10,
    "prediction_postprocessing": "None; negative forecasts if any are disclosed, not clipped",
}


def fit_candidate(series, config, stop):
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    samples = [
        (d, r1.feature_row(series, d, POLICY))
        for d in sorted(series)
        if d <= stop and series[d]["eligible"] and r1.donor(series, d, stop + timedelta(days=2))
    ]
    samples = [(d, f) for d, f in samples if f]
    if len(samples) < 60:
        raise ValueError("Insufficient eligible training rows")
    family = config["family"]
    if family == "autoregression":
        model = make_pipeline(StandardScaler(), LinearRegression())
    elif family == "random_forest":
        model = RandomForestRegressor(**config["parameters"])
    elif family == "gradient_boosting":
        model = GradientBoostingRegressor(**config["parameters"])
    else:
        raise ValueError("Unknown model family")
    model.fit([f["x"] for _, f in samples], [series[d]["value"] for d, _ in samples])
    return model, {"rows": len(samples), "last_label": str(samples[-1][0]), "cutoff": str(stop)}


def select_training(series):
    predictions = {c["id"]: {} for c in CANDIDATES}
    folds = []
    for year in (2021, 2022, 2023):
        first = date(year, 1, 1)
        days = [
            d
            for d in sorted(series)
            if d.year == year
            and series[d]["eligible"]
            and r1.feature_row(series, d, "complete") is not None
        ]
        if len(days) < 10:
            raise ValueError("Insufficient common training-fold dates")
        infos = []
        for config in CANDIDATES:
            model, info = fit_candidate(series, config, first - timedelta(days=2))
            predicted = r1.evaluate(model, series, POLICY, days)
            if set(predicted) != set(days):
                raise ValueError("Training candidate coverage mismatch")
            predictions[config["id"]].update(predicted)
            infos.append({"candidate": config["id"], **info})
        folds.append(
            {"start": str(first), "end": f"{year}-12-31", "common_dates": len(days), "fits": infos}
        )
    scores = []
    for config in CANDIDATES:
        predicted = predictions[config["id"]]
        days = sorted(predicted)
        scores.append(
            {
                **config,
                **r1.metrics([series[d]["value"] for d in days], [predicted[d] for d in days]),
            }
        )
    selected = {}
    for family in ("autoregression", "random_forest", "gradient_boosting"):
        selected[family] = min(
            (c for c in scores if c["family"] == family), key=lambda c: (c["mae"], c["id"])
        )
    return selected, scores, folds


def export_tree(estimator):
    tree = estimator.tree_
    return {
        "left": tree.children_left.tolist(),
        "right": tree.children_right.tolist(),
        "feature": tree.feature.tolist(),
        "threshold": tree.threshold.tolist(),
        "value": tree.value[:, 0, 0].tolist(),
    }


def tree_predict(tree, x):
    # sklearn tree inference casts input to float32, including split-boundary values.
    x = [struct.unpack("f", struct.pack("f", v))[0] for v in x]
    node = 0
    while tree["left"][node] != -1:
        node = (
            tree["left"][node]
            if x[tree["feature"][node]] <= tree["threshold"][node]
            else tree["right"][node]
        )
    return tree["value"][node]


def export_model(model, config, info):
    family = config["family"]
    result = {
        "family": family,
        "configuration": config,
        "feature_names": r1.FEATURES,
        "input_policy": POLICY,
        **info,
    }
    if family == "autoregression":
        scaler, fitted = model.steps[0][1], model.steps[1][1]
        result.update(
            mean=scaler.mean_.tolist(),
            scale=scaler.scale_.tolist(),
            coefficients=fitted.coef_.tolist(),
            intercept=float(fitted.intercept_),
        )
    else:
        result["trees"] = [
            export_tree(e)
            for e in (model.estimators_ if family == "random_forest" else model.estimators_[:, 0])
        ]
        result["feature_importances"] = model.feature_importances_.tolist()
        if family == "gradient_boosting":
            result.update(
                initial=float(model.init_.constant_[0, 0]), learning_rate=float(model.learning_rate)
            )
    return result


def predict_saved(model, x):
    if model["family"] == "autoregression":
        return r1.predict_saved(model, x)
    values = [tree_predict(tree, x) for tree in model["trees"]]
    if model["family"] == "random_forest":
        return sum(values) / len(values)
    if model["family"] == "gradient_boosting":
        return model["initial"] + model["learning_rate"] * sum(values)
    raise ValueError("Unknown saved model family")


def summarize(predictions):
    common = [
        r for r in predictions if r["actual"] is not None and all(r[m] is not None for m in MODELS)
    ]
    scores = []
    for name in MODELS:
        own = [r for r in predictions if r["actual"] is not None and r[name] is not None]
        scores.append(
            {
                "model": name,
                "calendar_forecasts": sum(r[name] is not None for r in predictions),
                "negative_forecasts": sum(r[name] is not None and r[name] < 0 for r in predictions),
                "own_dates": r1.metrics([r["actual"] for r in own], [r[name] for r in own]),
                "common_dates": r1.metrics(
                    [r["actual"] for r in common], [r[name] for r in common]
                ),
            }
        )
    return scores


def run(data, reference):
    if hashlib.sha256(data).hexdigest() != BUNDLE_SHA:
        raise ValueError("Release 2 requires the exact frozen Release 1 input")
    if reference["experiment_id"] != REFERENCE_ID or reference["selected"]["policy"] != POLICY:
        raise ValueError("Unexpected Release 1 reference")
    manifest, series, coverage = r1.read_input(data)
    if manifest["snapshot_id"] != SNAPSHOT_ID or max(series) > r1.VAL_END:
        raise ValueError("Snapshot or test isolation mismatch")
    selected, cv, folds = select_training(series)
    expected_dates = {r["date"] for r in reference["predictions"]}
    dates = [d for d in sorted(series) if d > r1.TRAIN_END]
    if expected_dates != {str(d) for d in dates} or len(dates) != 366:
        raise ValueError("Reference calendar mismatch")
    for fold, old in zip(folds, reference["folds"], strict=True):
        if (fold["start"], fold["common_dates"]) != (old["start"], old["common_dates"]):
            raise ValueError("Release 1 training scoring dates mismatch")
    if any(c["n"] != reference["selected"]["n"] for c in cv):
        raise ValueError("Training score denominators differ")
    # Lock the candidate from TRAINING outcomes before reading validation performance.
    ranking = [
        {
            "family": "ridge",
            "id": "release1_locked_ridge",
            **{k: reference["selected"][k] for k in ("mae", "rmse", "bias", "n")},
        },
        *selected.values(),
    ]
    ranking.sort(key=lambda c: (c["mae"], c["id"]))
    models, predicted, model_info, checks = {}, {}, {}, {}
    for family, config in selected.items():
        model, info = fit_candidate(series, config, r1.TRAIN_END - timedelta(days=1))
        saved = export_model(model, config, info)
        predicted[family] = r1.evaluate(model, series, POLICY, dates)
        difference = max(
            (
                abs(value - predict_saved(saved, r1.feature_row(series, d, POLICY)["x"]))
                for d, value in predicted[family].items()
            ),
            default=0,
        )
        if difference > 1e-8:
            raise ValueError("Saved model inference mismatch")
        models[family], checks[family] = saved, difference
        model_info[family] = {
            **info,
            "configuration": config,
            "feature_importances": saved.get("feature_importances"),
        }
    predictions = []
    ridge_difference = 0
    for old in reference["predictions"]:
        day = date.fromisoformat(old["date"])
        f = r1.feature_row(series, day, POLICY)
        if series[day]["value"] != old["actual"]:
            raise ValueError("Reference target changed")
        ridge = r1.predict_saved(reference["model"], f["x"]) if f else None
        if (ridge is None) != (old["ridge"] is None):
            raise ValueError("Reference Ridge coverage mismatch")
        if ridge is not None:
            ridge_difference = max(ridge_difference, abs(ridge - old["ridge"]))
        row = {k: old[k] for k in ("date", "actual", "latest_report", "weekly", "ridge")}
        row.update({m: values.get(day) for m, values in predicted.items()})
        row["latest_donor"] = f["latest_donor"] if f else None
        row["replaced_inputs"] = f["replaced_inputs"] if f else None
        predictions.append(row)
    if ridge_difference > 1e-8:
        raise ValueError("Locked Release 1 Ridge reproduction mismatch")
    models["ridge"] = {"family": "ridge", **reference["model"]}
    validation = summarize(predictions)
    report = {
        "release": "Release 2",
        "protocol": PROTOCOL,
        "snapshot_id": SNAPSHOT_ID,
        "reference_experiment_id": REFERENCE_ID,
        "code_sha256": {
            p.name: hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
            for p in (Path(__file__), Path(r1.__file__))
        },
        "runtime": {
            "python": platform.python_version(),
            "sklearn": version("scikit-learn"),
            "numpy": version("numpy"),
        },
        "coverage": coverage,
        "selected": selected,
        "training_cv": cv,
        "folds": folds,
        "training_ranking": ranking,
        "training_selected_finalist": ranking[0]["family"],
        "models_sha256": hashlib.sha256(encode(models)).hexdigest(),
        "models": model_info,
        "validation": validation,
        "predictions": predictions,
        "feature_names": r1.FEATURES,
        "strict_availability_feature_days": sum(
            r1.feature_row(series, d, POLICY, strict=True) is not None for d in dates
        ),
        "reserved_test": {
            "year": 2025,
            "status": "not_evaluated",
            "metrics": None,
            "predictions": None,
        },
        "checks": {
            "same_frozen_input": True,
            "training_scoring_matches_release1": True,
            "no_test_labels_in_series": max(series) <= r1.VAL_END,
            "no_test_predictions": all(r["date"] <= str(r1.VAL_END) for r in predictions),
            "neon_writes": 0,
            "validation_calendar_days": len(dates),
            "common_validation_days": validation[0]["common_dates"]["n"],
            "saved_model_max_difference": checks,
            "ridge_reference_max_difference": ridge_difference,
        },
        "limitations": [
            (
                "Historical publication times are unknown; this is an assumed "
                "retrospective reporting-delay scenario, not verified live "
                "forecasting accuracy."
            ),
            (
                "Current canonical revisions are used; original targets and missing "
                "dates remain unchanged."
            ),
            (
                "The 2024 validation period has already been examined; no 2025 "
                "final-test outcomes are used."
            ),
            (
                "Fixed Release 1 features and missing-input policy isolate model-"
                "family differences; this is a bounded comparison, not an exhaustive"
                " model search."
            ),
            (
                "The training-selected finalist is provisional; validation ranks are"
                " descriptive and do not retune or replace it."
            ),
            (
                "Forecast errors are conditional on available inputs and targets; "
                "own-date scores use different samples."
            ),
            (
                "Tree impurity importance describes this fitted model, not a causal "
                "effect or an unbiased measure of predictive value."
            ),
            (
                "No prediction intervals, significance claim or operational model "
                "deployment is delivered in this release."
            ),
        ],
    }
    report["experiment_id"] = hashlib.sha256(encode(report)).hexdigest()
    return report, models


def markdown(report):
    lines = [
        "# Release 2 execution report",
        "",
        (
            "National energy generated, million kWh. Training 2020–2023; "
            "validation 2024; final 2025 test reserved and not evaluated."
        ),
        "",
        (
            "Retrospective reporting-delay scenario: issue noon Bangladesh T-1, "
            "latest input T-2. Historical publication times are unknown, so "
            "these are not verified live forecast results."
        ),
        "",
        f"Snapshot: `{report['snapshot_id']}`",
        "",
        f"Experiment: `{report['experiment_id']}`",
        "",
        f"Training-selected provisional finalist: **{report['training_selected_finalist']}**.",
        "",
        "## Validation on identical dates",
        "",
        "| Model | Common dates | MAE | RMSE | Bias | Own scored | Calendar forecasts |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["validation"]:
        m = row["common_dates"]
        lines.append(
            f"| {row['model']} | {m['n']} | {m['mae']} | {m['rmse']} | "
            f"{m['bias']} | {row['own_dates']['n']} | {row['calendar_forecasts']} |"
        )
    lines += ["", "## Executed checks", ""]
    lines += [f"- {k}: {v}" for k, v in report["checks"].items()]
    lines += [
        "- Strict publication-time feature coverage: "
        f"{report['strict_availability_feature_days']}/366",
        "",
        "## Limitations",
        "",
    ]
    lines += ["- " + text for text in report["limitations"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--online", action="store_true")
    group.add_argument("--bundle", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/experiments/release2")
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
                raise ValueError("Frozen Release 1 input unavailable")
            path = output / "frozen_input.zip"
            download(service, found[0]["id"], path)
            if digest(path) != BUNDLE_SHA:
                raise ValueError("Frozen input bytes changed")
            data = path.read_bytes()
        else:
            data = args.bundle.read_bytes()
        from app.api.experiments import load_experiment

        reference = load_experiment()
        report, models = run(data, reference)
        files = {
            "frozen_input.zip": data,
            "experiment.json": encode(report),
            "experiment.json.gz": gzip.compress(encode(report), mtime=0),
            "models.json": encode(models),
            "models.json.gz": gzip.compress(encode(models), mtime=0),
            "validation_predictions.csv": r1.csv_bytes(report["predictions"]),
            "training_selection.csv": r1.csv_bytes(report["training_cv"]),
            "test_report.md": markdown(report).encode(),
        }
        for name, value in files.items():
            (output / name).write_bytes(value)
        manifest = {
            "experiment_id": report["experiment_id"],
            "snapshot_id": SNAPSHOT_ID,
            "files": {
                n: {"bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()}
                for n, v in files.items()
            },
        }
        (output / "manifest.json").write_bytes(encode(manifest))
        if args.online:
            from ingestion.drive_sync import upload_blob

            receipt = {
                n: upload_blob(service, folder, output / n) for n in (*files, "manifest.json")
            }
            (output / "storage_receipt.json").write_bytes(encode(receipt))
            upload_blob(service, folder, output / "storage_receipt.json")
        print(
            json.dumps(
                {
                    k: report[k]
                    for k in ("experiment_id", "training_selected_finalist", "validation", "checks")
                },
                indent=2,
            ),
            flush=True,
        )
    finally:
        if service is not None:
            service.close()


if __name__ == "__main__":
    main()
