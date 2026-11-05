"""Locked 2025 final evaluation. Repeated hosted runs restore the retained result."""

import argparse
import csv
import gzip
import hashlib
import io
import json
import platform
import random
import zipfile
from datetime import date, timedelta
from importlib.metadata import version
from pathlib import Path

from app.api.preparation import encode

from research import release1 as r1
from research import release2 as r2

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_ID = "c22ee6e06c2e26c40ee4f1754c083760b3de585e03c70b59a95fa91457b8eac6"
FIRST, LAST = date(2025, 1, 1), date(2025, 12, 31)
FIT_END = FIRST - timedelta(days=2)
PRIMARY = "autoregression"
BLOCKS, REPLICATES, SEED = (7, 14, 28), 2000, 20261105
PROTOCOL = {
    "version": "release3_final_v1",
    "target": "energy_generated",
    "unit": "million_kWh",
    "source_bundle_sha256": r2.BUNDLE_SHA,
    "snapshot_id": r2.SNAPSHOT_ID,
    "release2_experiment_id": REFERENCE_ID,
    "primary_model": PRIMARY,
    "selection": "Locked Release 2 training-selected OLS; no test selection",
    "input_policy": r2.POLICY,
    "feature_names": r1.FEATURES,
    "fit_start": str(r1.START),
    "fit_end": str(FIT_END),
    "test_start": str(FIRST),
    "test_end": str(LAST),
    "issue": r1.PROTOCOL["forecast_issue"],
    "latest_input_lag_days": 2,
    "reporting_scenario": r1.PROTOCOL["reporting_scenario"],
    "refitting": "All learned families refit once on eligible 2020-2024 labels through 2024-12-30",
    "parameter_updates_in_test": False,
    "test_inputs": (
        "Past original test-year observations may enter later target features, under T-2 cutoff"
    ),
    "primary_comparison": (
        "OLS versus exact lag-2 benchmark on the all-six-method common target dates"
    ),
    "scores": ["MAE", "RMSE", "signed bias", "own-date scores", "calendar forecast coverage"],
    "settings": {
        "ridge_alpha": 0.1,
        "ols": "LinearRegression with train-only StandardScaler",
        "random_forest_id": "rf_depth_8",
        "gradient_boosting_id": "gb_depth_2",
    },
    "bootstrap": {
        "method": "paired circular calendar-block percentile sensitivity",
        "block_lengths": BLOCKS,
        "replicates": REPLICATES,
        "seed": SEED,
        "contrast": "mean absolute error OLS minus lag 2 on all-method common dates",
        "percentiles": [2.5, 97.5],
        "gaps": "Missing/unmatched calendar rows retained as unscored",
        "interpretation": (
            "Descriptive dependence sensitivity, not a calibrated forecast "
            "interval or significance claim"
        ),
    },
    "postprocessing": "None; no clipping, target imputation or post-test retuning",
}


def code_hashes():
    return {
        p.name: hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
        for p in (Path(__file__), Path(r1.__file__), Path(r2.__file__))
    }


def evaluation_key():
    return hashlib.sha256(encode({"protocol": PROTOCOL, "code_sha256": code_hashes()})).hexdigest()


def read_final_input(data):
    # Validate the frozen manifest, audit, dimensions and historical portion first.
    manifest, series, coverage = r1.read_input(data)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        original = json.loads(z.read("original_snapshot.json"))
        audit = list(csv.DictReader(io.StringIO(z.read("daily_audit.csv").decode("utf-8-sig"))))
    by_date = {d["operational_date"]: d for d in original}
    for row in audit:
        day = date.fromisoformat(row["operational_date"])
        if day < FIRST:
            continue
        d = by_date.get(str(day))
        matches = [m for m in d["measurements"] if m["metric"] == "energy_generated"] if d else []
        m = matches[0] if matches else None
        source = (
            next((s for s in d["sources"] if m and s["id"] == m["source_id"]), None) if d else None
        )
        if m and (
            (m["unit"], m["period"], m["zone"], m["fuel"])
            != ("million_kWh", "daily", "national", None)
            or source is None
        ):
            raise ValueError("Final-year energy dimensions or lineage mismatch")
        eligible = row["observed_target_candidate"] == "True"
        series[day] = {
            "value": float(m["value"]) if eligible else None,
            "original": m["value"] if m else None,
            "eligible": eligible,
            "available_at": d["available_at"] if d else None,
            "version_id": d["report_version_id"] if d else None,
            "source_sha256": source["sha256"] if source else None,
        }
    if sorted(series) != [r1.START + timedelta(days=i) for i in range((LAST - r1.START).days + 1)]:
        raise ValueError("Dense final-evaluation calendar required")
    return manifest, series, coverage


def locked_configurations(reference):
    if (
        reference["experiment_id"] != REFERENCE_ID
        or reference["training_selected_finalist"] != PRIMARY
        or reference["snapshot_id"] != r2.SNAPSHOT_ID
    ):
        raise ValueError("Unexpected model-selection reference")
    configs = {
        family: reference["selected"][family]
        for family in ("autoregression", "random_forest", "gradient_boosting")
    }
    expected = {
        "autoregression": "ols",
        "random_forest": "rf_depth_8",
        "gradient_boosting": "gb_depth_2",
    }
    for family, config in configs.items():
        candidate = next(c for c in r2.CANDIDATES if c["id"] == expected[family])
        if (
            config["id"] != candidate["id"]
            or config["family"] != family
            or config["parameters"] != candidate["parameters"]
        ):
            raise ValueError("Locked settings changed")
    return configs


def fit_models(series, configurations):
    models, saved, info = {}, {}, {}
    for family, config in configurations.items():
        model, fit = r2.fit_candidate(series, config, FIT_END)
        models[family] = model
        saved[family] = r2.export_model(model, config, fit)
        info[family] = {
            **fit,
            "configuration_id": config["id"],
            "feature_importances": saved[family].get("feature_importances"),
        }
    model, fit = r1.fit(series, r2.POLICY, 0.1, FIT_END)
    fit["cutoff"] = str(FIT_END)
    scaler, fitted = model.steps[0][1], model.steps[1][1]
    saved["ridge"] = {
        "family": "ridge",
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coefficients": fitted.coef_.tolist(),
        "intercept": float(fitted.intercept_),
        "alpha": 0.1,
        "input_policy": r2.POLICY,
        "feature_names": r1.FEATURES,
        **fit,
    }
    models["ridge"] = model
    info["ridge"] = {**fit, "configuration_id": "ridge_alpha_0.1", "feature_importances": None}
    if any(date.fromisoformat(m["last_label"]) >= FIRST for m in info.values()):
        raise ValueError("Test label leaked into fitted model")
    return models, saved, info


def saved_predict(model, features):
    return (
        r1.predict_saved(model, features)
        if model["family"] == "ridge"
        else r2.predict_saved(model, features)
    )


def percentile(values, probability):
    values = sorted(values)
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def paired_bootstrap(predictions):
    # Resample calendar blocks, including unscored rows; never close calendar gaps.
    differences = [
        abs(r[PRIMARY] - r["actual"]) - abs(r["latest_report"] - r["actual"])
        if r["actual"] is not None and all(r[m] is not None for m in r2.MODELS)
        else None
        for r in predictions
    ]
    observed = [v for v in differences if v is not None]
    output = []
    for length in BLOCKS:
        rng = random.Random(SEED + length)
        estimates = []
        for _ in range(REPLICATES):
            indices = []
            while len(indices) < len(differences):
                start = rng.randrange(len(differences))
                indices.extend((start + i) % len(differences) for i in range(length))
            sample = [
                differences[i] for i in indices[: len(differences)] if differences[i] is not None
            ]
            if sample:
                estimates.append(sum(sample) / len(sample))
        output.append(
            {
                "block_days": length,
                "common_dates": len(observed),
                "point_difference": sum(observed) / len(observed) if observed else None,
                "lower_2_5": percentile(estimates, 0.025) if estimates else None,
                "upper_97_5": percentile(estimates, 0.975) if estimates else None,
                "requested_replicates": REPLICATES,
                "valid_replicates": len(estimates),
            }
        )
    return output


def run(data, reference):
    if hashlib.sha256(data).hexdigest() != r2.BUNDLE_SHA:
        raise ValueError("Exact frozen input required")
    configs = locked_configurations(reference)
    manifest, series, coverage = read_final_input(data)
    if manifest["snapshot_id"] != r2.SNAPSHOT_ID:
        raise ValueError("Final-evaluation snapshot changed")
    # Fit exactly once BEFORE computing any 2025 performance.
    models, saved, info = fit_models(series, configs)
    dates = [FIRST + timedelta(days=i) for i in range((LAST - FIRST).days + 1)]
    forecasts = {
        name: r1.evaluate(model, series, r2.POLICY, dates) for name, model in models.items()
    }
    predictions, features, checks = [], [], {name: 0 for name in models}
    for day in dates:
        f = r1.feature_row(series, day, r2.POLICY)
        latest = r1.donor(series, day - timedelta(days=2), day)
        weekly = r1.donor(series, day - timedelta(days=7), day)
        row = {
            "date": str(day),
            "actual": series[day]["value"],
            "latest_report": latest[0] if latest else None,
            "weekly": weekly[0] if weekly else None,
            **{name: values.get(day) for name, values in forecasts.items()},
            "latest_donor": f["latest_donor"] if f else None,
            "replaced_inputs": f["replaced_inputs"] if f else None,
            "unknown_availability_inputs": f["unknown_availability_inputs"] if f else None,
        }
        if f:
            if date.fromisoformat(f["latest_donor"]) > day - timedelta(days=2):
                raise ValueError("Future test-year donor")
            for name in models:
                checks[name] = max(
                    checks[name], abs(row[name] - saved_predict(saved[name], f["x"]))
                )
        predictions.append(row)
        features.append(
            {
                "date": str(day),
                "eligible_target": series[day]["eligible"],
                "original_target": series[day]["original"],
                **dict(zip(r1.FEATURES, f["x"] if f else [None] * len(r1.FEATURES), strict=True)),
                "latest_donor": row["latest_donor"],
                "replaced_inputs": row["replaced_inputs"],
            }
        )
    if any(v > 1e-8 for v in checks.values()):
        raise ValueError("Final model serialization mismatch")
    scores = r2.summarize(predictions)
    monthly = []
    for month in range(1, 13):
        rows = [r for r in predictions if r["date"].startswith(f"2025-{month:02d}")]
        monthly.append(
            {
                "month": f"2025-{month:02d}",
                "calendar_days": len(rows),
                "observed_targets": sum(r["actual"] is not None for r in rows),
                "scores": r2.summarize(rows),
            }
        )
    report = {
        "release": "Release 3",
        "stage": "final_historical_evaluation",
        "evaluation_key": evaluation_key(),
        "protocol": PROTOCOL,
        "snapshot_id": r2.SNAPSHOT_ID,
        "reference_experiment_id": REFERENCE_ID,
        "primary_model": PRIMARY,
        "code_sha256": code_hashes(),
        "runtime": {
            "python": platform.python_version(),
            "sklearn": version("scikit-learn"),
            "numpy": version("numpy"),
        },
        "coverage": coverage,
        "models": info,
        "models_sha256": hashlib.sha256(encode(saved)).hexdigest(),
        "feature_names": r1.FEATURES,
        "scores": scores,
        "monthly": monthly,
        "paired_mae_sensitivity": paired_bootstrap(predictions),
        "predictions": predictions,
        "strict_availability_feature_days": sum(
            r1.feature_row(series, d, r2.POLICY, strict=True) is not None for d in dates
        ),
        "final_test": {
            "year": 2025,
            "status": "evaluated_locked_protocol",
            "selection_changed": False,
        },
        "checks": {
            "same_frozen_input": True,
            "locked_release2_settings": True,
            "no_test_labels_in_fit": True,
            "no_test_parameter_updates": True,
            "all_donors_at_or_before_t_minus_2": True,
            "neon_writes": 0,
            "calendar_days": len(dates),
            "common_scored_dates": scores[0]["common_dates"]["n"],
            "saved_model_max_difference": checks,
        },
        "limitations": [
            (
                "Historical publication times are unknown; results assume the "
                "retrospective reporting-delay scenario and do not establish "
                "verified live forecasting accuracy."
            ),
            (
                "The current canonical snapshot may contain revisions unavailable "
                "historically; this is not a verified point-in-time backtest."
            ),
            (
                "Earlier 2025 observations are used only as past inputs for later "
                "origins; no 2025 label is used to fit or update model parameters."
            ),
            (
                "Missing and held evaluation targets remain unscored. Coverage and"
                " common-date errors are necessary for interpretation."
            ),
            (
                "Circular calendar-block intervals are descriptive sensitivity to "
                "short-range error dependence. Wrap-around, seasonality, "
                "nonstationarity and missingness can affect them; they are not "
                "forecast prediction intervals or calibrated significance tests."
            ),
            (
                "The primary OLS model remains fixed even if another method scores"
                " better. Test results must not be used for further selection or "
                "retuning."
            ),
            (
                "This is one historical test year and one bounded set of models; "
                "no universal model-superiority or causal conclusion is supported."
            ),
            (
                "Saved research models and historical forecasts are delivered; "
                "prospective operational deployment and future prediction "
                "intervals remain separate work."
            ),
        ],
    }
    report["experiment_id"] = hashlib.sha256(encode(report)).hexdigest()
    return report, saved, features


def markdown(report):
    lines = [
        "# Release 3 — locked 2025 final evaluation",
        "",
        (
            "Target: national daily energy generated, million kWh. Fit "
            "2020–2024 through 2024-12-30; evaluate 2025 with fixed model "
            "parameters."
        ),
        "",
        (
            "Primary model: autoregressive OLS, selected in Release 2 before "
            "final-year scoring. No post-test model switching or retuning."
        ),
        "",
        (
            "Historical reporting times are unknown. Issue noon Bangladesh "
            "T-1, latest original input T-2, under an explicit retrospective "
            "assumption. These results do not verify live forecasting "
            "accuracy."
        ),
        "",
        f"Snapshot: `{report['snapshot_id']}`",
        "",
        f"Experiment: `{report['experiment_id']}`",
        "",
        "## Final test — identical dates",
        "",
        "| Method | Common dates | MAE | RMSE | Bias | Own scored | Calendar forecasts |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["scores"]:
        m = row["common_dates"]
        lines.append(
            f"| {row['model']} | {m['n']} | {m['mae']} | {m['rmse']} | "
            f"{m['bias']} | {row['own_dates']['n']} | {row['calendar_forecasts']} |"
        )
    lines += [
        "",
        "## Paired MAE sensitivity: OLS minus lag 2",
        "",
        (
            "Negative differences favor OLS; percentile ranges are "
            "descriptive, not forecast intervals or significance tests."
        ),
        "",
        "| Calendar block | Common dates | Difference | 2.5th percentile | 97.5th percentile |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in report["paired_mae_sensitivity"]:
        lines.append(
            f"| {r['block_days']} | {r['common_dates']} | {r['point_difference']} | "
            f"{r['lower_2_5']} | {r['upper_97_5']} |"
        )
    lines += ["", "## Executed checks", ""]
    lines += [f"- {k}: {v}" for k, v in report["checks"].items()]
    lines += [
        "- Strict publication-time feature coverage: "
        f"{report['strict_availability_feature_days']}/365",
        "",
        "## Limitations",
        "",
    ]
    lines += ["- " + text for text in report["limitations"]]
    return "\n".join(lines) + "\n"


def final_registry(service, folder):
    result = (
        service.files()
        .list(
            q=(
                f"'{folder}' in parents and trashed=false "
                "and appProperties has {key='bpdb_role' and value='release3_final_evaluation'}"
            ),
            fields="nextPageToken,files(id)",
            pageSize=100,
        )
        .execute(num_retries=3)
    )
    matches = result.get("files", [])
    if result.get("nextPageToken") or len(matches) > 1:
        raise ValueError("Duplicate final-evaluation receipts require review")
    if not matches:
        return None
    data = json.loads(service.files().get_media(fileId=matches[0]["id"]).execute(num_retries=3))
    if data["evaluation_key"] != evaluation_key():
        raise ValueError(
            "A different final evaluation is already retained; do not retune against test"
        )
    return data


def restore_result(service, registry, output):
    from ingestion.drive_sync import digest, download

    for name, spec in registry["files"].items():
        if Path(name).name != name or name.startswith("."):
            raise ValueError("Unsafe saved result path")
        path = output / name
        download(service, spec["id"], path)
        if digest(path) != spec["sha256"] or path.stat().st_size != spec["size"]:
            raise ValueError("Saved final-evaluation checksum mismatch")
    report = json.loads((output / "experiment.json").read_bytes())
    if report["experiment_id"] != registry["experiment_id"]:
        raise ValueError("Saved final-evaluation identity mismatch")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--online", action="store_true")
    group.add_argument("--bundle", type=Path, help="Reproduce the locked protocol; never retune")
    parser.add_argument("--output", type=Path, default=ROOT / "data/experiments/release3")
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    service = None
    try:
        if args.online:
            from ingestion.drive_sync import digest, download, find_files
            from ingestion.online_recovery import drive_service

            service, folder = drive_service()
            registry = final_registry(service, folder)
            if registry:
                report = restore_result(service, registry, output)
                print(
                    json.dumps(
                        {
                            "status": "restored_existing_final_evaluation",
                            "experiment_id": report["experiment_id"],
                        }
                    ),
                    flush=True,
                )
                return
            found = find_files(service, folder, "blob", r2.BUNDLE_SHA)
            if len(found) != 1:
                raise ValueError("Frozen input unavailable")
            path = output / "frozen_input.zip"
            download(service, found[0]["id"], path)
            if digest(path) != r2.BUNDLE_SHA:
                raise ValueError("Frozen input changed")
            data = path.read_bytes()
        else:
            data = args.bundle.read_bytes()
        from app.api.experiments import load_comparison

        report, models, features = run(data, load_comparison())
        files = {
            "frozen_input.zip": data,
            "experiment.json": encode(report),
            "experiment.json.gz": gzip.compress(encode(report), mtime=0),
            "models.json": encode(models),
            "models.json.gz": gzip.compress(encode(models), mtime=0),
            "test_predictions.csv": r1.csv_bytes(report["predictions"]),
            "test_features.csv": r1.csv_bytes(features),
            "test_report.md": markdown(report).encode(),
        }
        manifest = {
            "experiment_id": report["experiment_id"],
            "evaluation_key": report["evaluation_key"],
            "files": {
                n: {"bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()}
                for n, v in files.items()
            },
        }
        files["manifest.json"] = encode(manifest)
        for name, value in files.items():
            (output / name).write_bytes(value)
        if args.online:
            from googleapiclient.http import MediaIoBaseUpload
            from ingestion.drive_sync import upload_blob

            receipts = {n: upload_blob(service, folder, output / n) for n in files}
            registry = {
                "evaluation_key": report["evaluation_key"],
                "experiment_id": report["experiment_id"],
                "files": receipts,
            }
            payload = encode(registry)
            service.files().create(
                body={
                    "name": "bpdb-release3-final-evaluation.json",
                    "parents": [folder],
                    "appProperties": {"bpdb_role": "release3_final_evaluation"},
                },
                media_body=MediaIoBaseUpload(io.BytesIO(payload), mimetype="application/json"),
                fields="id",
            ).execute(num_retries=3)
            if final_registry(service, folder) != registry:
                raise ValueError("Final-evaluation receipt verification failed")
            (output / "storage_receipt.json").write_bytes(payload)
        print(
            json.dumps(
                {
                    k: report[k]
                    for k in (
                        "experiment_id",
                        "primary_model",
                        "scores",
                        "paired_mae_sensitivity",
                        "checks",
                    )
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
