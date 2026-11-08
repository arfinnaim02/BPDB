"""Read-only, integrity-checked missing-input study; never fit or impute in a request."""

import gzip
import hashlib
import io
import json
import zlib
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Response

from app.api.preparation import encode

router = APIRouter(prefix="/api/v1/research", tags=["Missing-data treatment"])
ASSETS = Path(__file__).resolve().parents[1] / "data"
KINDS = ("summary", "masked_trials", "masked_windows", "training_calendar", "input_candidates")
Download = Literal[
    "summary",
    "masked_trials",
    "masked_windows",
    "training_calendar",
    "input_candidates",
    "report",
    "methods",
]


def unpack(path, limit):
    with gzip.GzipFile(fileobj=io.BytesIO(path.read_bytes())) as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Study asset too large")
    return data


def load_study():
    try:
        report = json.loads(unpack(ASSETS / "treatment_study.json.gz", 250_000))
        payload = {k: v for k, v in report.items() if k != "study_id"}
        checks = report["checks"]
        if (
            hashlib.sha256(encode(payload)).hexdigest() != report["study_id"]
            or report["protocol"]["version"] != "missing_input_treatment_v1"
            or report["protocol"]["end"] != "2023-12-31"
            or any(
                checks[k] != 0
                for k in (
                    "database_writes",
                    "forecast_models_trained",
                    "validation_test_rows_used",
                )
            )
            or not checks["all_donors_strictly_past"]
            or not checks["all_masks_eligible_training_originals"]
        ):
            raise ValueError("Study integrity/scope mismatch")
        return report
    except (OSError, EOFError, zlib.error, ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(503, "Verified missing-data treatment study unavailable") from None


@router.get("/treatment-study")
def treatment_study(download: Download | None = None):
    report = load_study()
    if download is None:
        return Response(
            encode(report), media_type="application/json", headers={"Cache-Control": "no-store"}
        )
    extension, media = "json", "application/json"
    if download in KINDS:
        try:
            data = unpack(ASSETS / f"treatment_{download}.csv.gz", 2_000_000)
            expected = report["exports"][download]
            if (
                len(data) != expected["bytes"]
                or hashlib.sha256(data).hexdigest() != expected["sha256"]
            ):
                raise ValueError("Study export differs")
        except (OSError, EOFError, zlib.error, ValueError, KeyError, TypeError):
            raise HTTPException(503, "Verified treatment export unavailable") from None
        extension, media = "csv", "text/csv"
    elif download == "methods":
        from research.treatment_study import markdown

        data, extension, media = markdown(report).encode(), "md", "text/markdown"
    else:
        data = encode(report)
    return Response(
        data,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="bpdb-treatment-{download}.{extension}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
