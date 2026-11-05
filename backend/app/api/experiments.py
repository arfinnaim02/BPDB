"""Verified frozen Release 1 results; no model fitting in a web request."""

import csv
import gzip
import hashlib
import io
import json
import zlib
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Response

from app.api.preparation import encode

router = APIRouter(prefix="/api/v1/research", tags=["Forecast experiments"])
ASSET = Path(__file__).resolve().parents[1] / "data" / "release1.json.gz"
Download = Literal["predictions", "selection", "report", "model", "test_report"]


def load_experiment():
    try:
        report = json.loads(gzip.decompress(ASSET.read_bytes()))
        fingerprint = {
            k: v
            for k, v in report.items()
            if k not in ("experiment_id", "full_history_readiness", "source_bundle_sha256")
        }
        if (
            hashlib.sha256(encode(fingerprint)).hexdigest() != report["experiment_id"]
            or report["reserved_test"]["status"] != "not_evaluated"
            or report["reserved_test"]["metrics"] is not None
            or report["reserved_test"]["predictions"] is not None
            or not report["test_report"]["no_test_predictions"]
            or any(r["date"] > "2024-12-31" for r in report["predictions"])
        ):
            raise ValueError("Experiment identity or test reservation mismatch")
        return report
    except (OSError, EOFError, zlib.error, ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(503, "Verified Release 1 results unavailable") from None


def prediction_csv(report):
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(
        [
            "Operational Date",
            "Observed target (million kWh)",
            "Latest report forecast (million kWh)",
            "Weekly forecast (million kWh)",
            "Ridge forecast (million kWh)",
        ]
    )
    for row in report["predictions"]:
        writer.writerow([row[k] for k in ("date", "actual", "latest_report", "weekly", "ridge")])
    return out.getvalue().encode("utf-8-sig")


@router.get("/release1")
def release1(download: Download | None = None):
    report = load_experiment()
    if download is None:
        return report
    from research.release1 import csv_bytes, test_markdown

    extension, media = "json", "application/json"
    if download == "predictions":
        data, extension, media = prediction_csv(report), "csv", "text/csv"
    elif download == "selection":
        data, extension, media = csv_bytes(report["training_cv"]), "csv", "text/csv"
    elif download == "test_report":
        data, extension, media = test_markdown(report).encode(), "md", "text/markdown"
    else:
        data = encode(report["model"] if download == "model" else report)
    return Response(
        data,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="bpdb-release1-{download}.{extension}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


COMPARISON_ASSET = ASSET.with_name("release2.json.gz")
MODELS_ASSET = ASSET.with_name("release2_models.json.gz")
ComparisonDownload = Literal["predictions", "selection", "models", "report", "test_report"]
COMPARISON_MODELS = (
    "latest_report",
    "weekly",
    "ridge",
    "autoregression",
    "random_forest",
    "gradient_boosting",
)


def load_comparison():
    try:
        report = json.loads(gzip.decompress(COMPARISON_ASSET.read_bytes()))
        fingerprint = {k: v for k, v in report.items() if k != "experiment_id"}
        if (
            hashlib.sha256(encode(fingerprint)).hexdigest() != report["experiment_id"]
            or report["reserved_test"]["status"] != "not_evaluated"
            or report["reserved_test"]["metrics"] is not None
            or report["reserved_test"]["predictions"] is not None
            or report["checks"]["neon_writes"] != 0
            or not report["checks"]["no_test_labels_in_series"]
            or not report["checks"]["no_test_predictions"]
            or len(report["predictions"]) != 366
            or any(not r["date"].startswith("2024-") for r in report["predictions"])
            or tuple(r["model"] for r in report["validation"]) != COMPARISON_MODELS
            or report["reference_experiment_id"] != load_experiment()["experiment_id"]
        ):
            raise ValueError("Release 2 identity or reservation mismatch")
        return report
    except (OSError, EOFError, zlib.error, ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(503, "Verified Release 2 results unavailable") from None


def comparison_models(report):
    try:
        data = gzip.decompress(MODELS_ASSET.read_bytes())
        if hashlib.sha256(data).hexdigest() != report["models_sha256"]:
            raise ValueError("Saved model checksum mismatch")
        return data
    except (OSError, EOFError, zlib.error, ValueError, KeyError):
        raise HTTPException(503, "Verified saved models unavailable") from None


def comparison_csv(report, kind):
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    if kind == "predictions":
        writer.writerow(
            [
                "Operational Date",
                "Observed target (million kWh)",
                *[f"{name} forecast (million kWh)" for name in COMPARISON_MODELS],
            ]
        )
        for row in report["predictions"]:
            writer.writerow(
                [row["date"], row["actual"], *[row[name] for name in COMPARISON_MODELS]]
            )
    else:
        writer.writerow(
            [
                "Candidate",
                "Model family",
                "Training scored dates",
                "MAE (million kWh)",
                "RMSE (million kWh)",
                "Bias (million kWh)",
                "Maximum depth",
                "Trees",
                "Learning rate",
                "Minimum leaf rows",
            ]
        )
        for row in report["training_cv"]:
            p = row["parameters"]
            writer.writerow(
                [row[k] for k in ("id", "family", "n", "mae", "rmse", "bias")]
                + [
                    p.get(k)
                    for k in ("max_depth", "n_estimators", "learning_rate", "min_samples_leaf")
                ]
            )
    return out.getvalue().encode("utf-8-sig")


@router.get("/release2")
def release2(download: ComparisonDownload | None = None):
    report = load_comparison()
    if download is None:
        return report
    extension, media = "json", "application/json"
    if download in ("predictions", "selection"):
        data, extension, media = comparison_csv(report, download), "csv", "text/csv"
    elif download == "models":
        data = comparison_models(report)
    elif download == "test_report":
        from research.release2 import markdown

        data, extension, media = markdown(report).encode(), "md", "text/markdown"
    else:
        data = encode(report)
    return Response(
        data,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="bpdb-release2-{download}.{extension}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
