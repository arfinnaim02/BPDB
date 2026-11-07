"""Authenticated report snapshots and bounded PDF/vector exports."""

import hashlib
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response

from app.api.monitoring import Database
from app.api.preparation import encode
from app.services.research_report import methods_markdown, read_report, tables_csv

router = APIRouter(prefix="/api/v1/research", tags=["Research reports"])
Export = Literal["pdf", "json", "tables", "methods", "figure"]
Figure = Literal["models", "daily", "monthly", "scatter"]


@router.get("/report")
def research_report(
    response: Response,
    session: Database,
    download: Export | None = None,
    figure: Figure = "models",
    expected_id: Annotated[str | None, Query(pattern="^[a-f0-9]{64}$")] = None,
):
    report = read_report(session)
    response.headers["Cache-Control"] = "no-store"
    if download is None:
        return report
    if expected_id != report["report_id"]:
        raise HTTPException(
            409, "Report inputs changed or no snapshot was selected; refresh the report preview"
        )
    if download == "pdf":
        from app.services.report_pdf import pdf_bytes

        data, extension, media = pdf_bytes(report), "pdf", "application/pdf"
    elif download == "figure":
        from app.services.report_pdf import svg_bytes

        data, extension, media = svg_bytes(report, figure), "svg", "image/svg+xml"
    elif download == "tables":
        data, extension, media = tables_csv(report), "csv", "text/csv"
    elif download == "methods":
        data, extension, media = methods_markdown(report).encode(), "md", "text/markdown"
    else:
        data, extension, media = encode(report), "json", "application/json"
    if len(data) > 3_500_000:
        raise HTTPException(503, "Report export exceeds the hosted size limit")
    name = figure if download == "figure" else download
    filename = f"bpdb-research-{report['report_id'][:12]}-{name}.{extension}"
    return Response(
        data,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Report-ID": report["report_id"],
            "X-Content-SHA256": hashlib.sha256(data).hexdigest(),
        },
    )
