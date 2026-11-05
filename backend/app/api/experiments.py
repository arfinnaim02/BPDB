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
