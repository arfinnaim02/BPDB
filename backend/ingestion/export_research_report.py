"""Read-only research report export, with optional verified private Drive archival."""

import argparse
import hashlib
import io
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.api.monitoring import read_session
from app.api.preparation import encode
from app.services.report_pdf import pdf_bytes, svg_bytes
from app.services.research_report import FIGURES, methods_markdown, read_report, tables_csv

ROOT = Path(__file__).resolve().parents[2]


def export_files(report, output):
    files = {
        "research_report.json": encode(report),
        "research_report.pdf": pdf_bytes(report),
        "methods_results.md": methods_markdown(report).encode(),
        "model_tables.csv": tables_csv(report),
    }
    files.update({"figure_" + name + ".svg": svg_bytes(report, name) for name in FIGURES})
    manifest = {
        "report_id": report["report_id"],
        "generated_at": report["generated_at"],
        "source_ids": report["source_ids"],
        "files": {
            n: {"bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()} for n, v in files.items()
        },
    }
    files["manifest.json"] = encode(manifest)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (output / name).write_bytes(data)
    return files


def archive_files(report, files, output):
    from googleapiclient.http import MediaIoBaseUpload

    from ingestion.drive_sync import upload_blob
    from ingestion.online_recovery import drive_service

    service, folder = drive_service()
    try:
        receipt = {
            "report_id": report["report_id"],
            "generated_at": report["generated_at"],
            "source_ids": report["source_ids"],
            "files": {name: upload_blob(service, folder, output / name) for name in files},
        }
        data = encode(receipt)
        name = (
            "BPDB research report "
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + " "
            + report["report_id"][:12]
            + ".json"
        )
        saved = (
            service.files()
            .create(
                body={
                    "name": name,
                    "parents": [folder],
                    "appProperties": {
                        "bpdb_role": "research_report_receipt",
                        "report_id": report["report_id"],
                    },
                },
                media_body=MediaIoBaseUpload(io.BytesIO(data), mimetype="application/json"),
                fields="id",
            )
            .execute(num_retries=3)
        )
        if service.files().get_media(fileId=saved["id"]).execute(num_retries=3) != data:
            raise ValueError("Report receipt verification failed")
        (output / "storage_receipt.json").write_bytes(data)
    finally:
        service.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "data/research_reports/latest")
    args = parser.parse_args()
    with contextmanager(read_session)() as session:
        report = read_report(session)
    files = export_files(report, args.output)
    if args.archive:
        archive_files(report, files, args.output)
    print(
        json.dumps(
            {
                "status": "exported",
                "report_id": report["report_id"],
                "files": len(files),
                "archive_verified": args.archive,
                "prospective_scored_dates": report["prospective"]["summary"]["scored_dates"],
                "master_dates": report["current_inventory"]["canonical_dates"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
