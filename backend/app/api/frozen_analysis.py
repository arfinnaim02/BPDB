"""Protected read-only access to the reviewed frozen descriptive analysis."""

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

router = APIRouter(prefix="/api/v1/analytics", tags=["Frozen research analysis"])
ASSET = Path(__file__).resolve().parents[1] / "data" / "frozen_2024_analysis.json.gz"
SNAPSHOT = "4f35dcb7da194025f79f2f7fb8ed52066e599c96f72e7cd0fc62c691fb4883a1"
Table = Literal["daily", "monthly", "quarterly", "weekday", "report"]


def load_analysis():
    try:
        report = json.loads(gzip.decompress(ASSET.read_bytes()))
        if not isinstance(report, dict):
            raise ValueError("Invalid frozen analysis shape")
        fingerprint = {k: v for k, v in report.items() if k != "analysis_id"}
        if (
            report["snapshot_id"] != SNAPSHOT
            or hashlib.sha256(encode(fingerprint)).hexdigest() != report["analysis_id"]
        ):
            raise ValueError("Frozen analysis identity mismatch")
        return report
    except (OSError, EOFError, zlib.error, ValueError, KeyError):
        raise HTTPException(503, "Verified frozen analysis is unavailable") from None


def table_csv(report, table):
    if table == "daily":
        columns = [
            ("Date", "date"),
            ("Original energy (million kWh)", "original_value"),
            ("Eligible observation", "eligible"),
            ("Complete trailing 7-day mean (million kWh)", "trailing_7_mean"),
        ]
    else:
        columns = [
            ("Period", "label"),
            ("Calendar days", "calendar_days"),
            ("Observed days", "observed_days"),
            ("Eligible days", "eligible_days"),
            ("Missing days", "missing_days"),
            ("Held days", "held_days"),
            ("Eligible coverage (%)", "coverage_percent"),
            ("Mean daily energy (million kWh)", "mean"),
            ("Median daily energy (million kWh)", "median"),
            ("Minimum daily energy (million kWh)", "minimum"),
            ("Maximum daily energy (million kWh)", "maximum"),
            ("Sample SD (million kWh)", "sample_sd"),
        ]
        if table != "weekday":
            columns.append(("Complete-period energy (million kWh)", "complete_total"))
        if table == "monthly":
            columns.append(("Complete-month total change (%)", "mom_total_percent"))
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow([title for title, _ in columns])
    for row in report[table]:
        writer.writerow([row.get(key) for _, key in columns])
    return out.getvalue().encode("utf-8-sig")


@router.get("/frozen-2024")
def frozen_analysis(download: Table | None = None):
    report = load_analysis()
    if download is None:
        return report
    data = encode(report) if download == "report" else table_csv(report, download)
    extension = "json" if download == "report" else "csv"
    return Response(
        data,
        media_type="application/json" if extension == "json" else "text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="bpdb-frozen-2024-'
            + download
            + "."
            + extension
            + '"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
