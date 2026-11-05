"""Authenticated frozen final-year results and clean thesis-table exports."""

import csv
import gzip
import hashlib
import io
import json
import zlib
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Response

from app.api.experiments import COMPARISON_MODELS, load_comparison
from app.api.preparation import encode

router = APIRouter(prefix="/api/v1/research", tags=["Final evaluation"])
ASSET = Path(__file__).resolve().parents[1] / "data/release3.json.gz"
MODELS_ASSET = ASSET.with_name("release3_models.json.gz")
Download = Literal[
    "predictions", "metrics", "monthly", "sensitivity", "models", "report", "test_report"
]
LABELS = {
    "latest_report": "Latest report (lag 2)",
    "weekly": "Same weekday (lag 7)",
    "ridge": "Ridge (refitted)",
    "autoregression": "Autoregressive OLS (primary)",
    "random_forest": "Random Forest",
    "gradient_boosting": "Gradient Boosting",
}


def load_final():
    try:
        d = json.loads(gzip.decompress(ASSET.read_bytes()))
        fingerprint = {k: v for k, v in d.items() if k != "experiment_id"}
        calendar = [str(date(2025, 1, 1) + timedelta(days=i)) for i in range(365)]
        if (
            hashlib.sha256(encode(fingerprint)).hexdigest() != d["experiment_id"]
            or d["final_test"]["status"] != "evaluated_locked_protocol"
            or d["final_test"]["selection_changed"] is not False
            or d["primary_model"] != "autoregression"
            or [r["date"] for r in d["predictions"]] != calendar
            or tuple(r["model"] for r in d["scores"]) != COMPARISON_MODELS
            or d["reference_experiment_id"] != load_comparison()["experiment_id"]
            or any(m["last_label"] > "2024-12-30" for m in d["models"].values())
            or not d["checks"]["no_test_labels_in_fit"]
            or not d["checks"]["no_test_parameter_updates"]
            or d["checks"]["neon_writes"] != 0
        ):
            raise ValueError("Final-evaluation identity or protocol mismatch")
        return d
    except (OSError, EOFError, zlib.error, ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(503, "Verified final-evaluation results unavailable") from None


def model_bytes(report):
    try:
        data = gzip.decompress(MODELS_ASSET.read_bytes())
        if hashlib.sha256(data).hexdigest() != report["models_sha256"]:
            raise ValueError("Final model checksum mismatch")
        return data
    except (OSError, EOFError, zlib.error, ValueError, KeyError):
        raise HTTPException(503, "Verified final models unavailable") from None


def export_csv(report, kind):
    out = io.StringIO(newline="")
    w = csv.writer(out)
    if kind == "predictions":
        w.writerow(
            [
                "Operational Date",
                "Observed Energy (million kWh)",
                *[LABELS[k] + " Forecast (million kWh)" for k in COMPARISON_MODELS],
            ]
        )
        for r in report["predictions"]:
            w.writerow([r["date"], r["actual"], *[r[k] for k in COMPARISON_MODELS]])
    elif kind == "metrics":
        w.writerow(
            [
                "Method",
                "Common Scored Dates",
                "Common MAE (million kWh)",
                "Common RMSE (million kWh)",
                "Common Bias (million kWh)",
                "Own Scored Dates",
                "Own MAE (million kWh)",
                "Own RMSE (million kWh)",
                "Calendar Forecasts",
                "Calendar Days",
                "Negative Forecasts",
            ]
        )
        for r in report["scores"]:
            c, own = r["common_dates"], r["own_dates"]
            w.writerow(
                [
                    LABELS[r["model"]],
                    c["n"],
                    c["mae"],
                    c["rmse"],
                    c["bias"],
                    own["n"],
                    own["mae"],
                    own["rmse"],
                    r["calendar_forecasts"],
                    365,
                    r["negative_forecasts"],
                ]
            )
    elif kind == "monthly":
        w.writerow(
            [
                "Month",
                "Method",
                "Common Scored Dates",
                "MAE (million kWh)",
                "RMSE (million kWh)",
                "Bias (million kWh)",
                "Calendar Forecasts",
                "Calendar Days",
            ]
        )
        for month in report["monthly"]:
            for r in month["scores"]:
                c = r["common_dates"]
                w.writerow(
                    [
                        month["month"],
                        LABELS[r["model"]],
                        c["n"],
                        c["mae"],
                        c["rmse"],
                        c["bias"],
                        r["calendar_forecasts"],
                        month["calendar_days"],
                    ]
                )
    else:
        w.writerow(
            [
                "Calendar Block Days",
                "Common Scored Dates",
                "OLS Minus Lag2 MAE (million kWh)",
                "Bootstrap 2.5 Percentile (million kWh)",
                "Bootstrap 97.5 Percentile (million kWh)",
                "Requested Resamples",
                "Valid Resamples",
            ]
        )
        for r in report["paired_mae_sensitivity"]:
            w.writerow(
                [
                    r[k]
                    for k in (
                        "block_days",
                        "common_dates",
                        "point_difference",
                        "lower_2_5",
                        "upper_97_5",
                        "requested_replicates",
                        "valid_replicates",
                    )
                ]
            )
    return out.getvalue().encode("utf-8-sig")


@router.get("/release3")
def final_evaluation(download: Download | None = None):
    report = load_final()
    if download is None:
        return report
    extension, media = "json", "application/json"
    if download in ("predictions", "metrics", "monthly", "sensitivity"):
        data, extension, media = export_csv(report, download), "csv", "text/csv"
    elif download == "models":
        data = model_bytes(report)
    elif download == "test_report":
        from research.release3 import markdown

        data, extension, media = markdown(report).encode(), "md", "text/markdown"
    else:
        data = encode(report)
    return Response(
        data,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="bpdb-release3-{download}.{extension}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
