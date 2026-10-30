"""Export canonical Page 1 national measurements from a Neon snapshot."""

import csv
import hashlib
import io
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.db.models import (
    DailyReport,
    ReportVersion,
    SourceDocument,
    VersionSource,
)
from app.db.session import session_factory
from sqlalchemy import select, text, union_all

from ingestion.import_page1_measurements import METRICS, TABLES

PROJECT_ROOT = Path(__file__).resolve().parents[2]

COLUMNS = {
    "day_peak_generation": "day_peak_generation_mw",
    "evening_peak_generation": "evening_peak_generation_mw",
    "minimum_generation": "minimum_generation_mw",
    "maximum_generation": "maximum_generation_mw",
    "energy_generated": "energy_generated_million_kwh",
    "day_peak_demand": "day_peak_demand_mw",
    "evening_peak_demand": "evening_peak_demand_mw",
    "energy_demand": "energy_demand_million_kwh",
    "energy_unserved": "energy_unserved_million_kwh",
    "gas_supplied": "gas_supplied_mmcfd",
    "production_cost_per_kwh": "production_cost_bdt_per_kwh",
    "total_production_cost": "total_production_cost_bdt",
    "maximum_temperature": "maximum_temperature_c",
}


def string_value(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def csv_bytes(fields, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=fields,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def main():
    factory = session_factory()

    print("Reading canonical records from Neon...", flush=True)

    with factory() as session:
        session.execute(text(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
        ))
        session.execute(text(
            "SET LOCAL statement_timeout = '60000'"
        ))

        versions = session.execute(
            select(
                DailyReport.report_date,
                ReportVersion.id.label("version_id"),
                ReportVersion.quality_status,
                ReportVersion.parser_version,
                ReportVersion.available_at,
            )
            .join(
                ReportVersion,
                (
                    ReportVersion.id == DailyReport.current_version_id
                ) & (
                    ReportVersion.report_id == DailyReport.id
                ),
            )
            .where(DailyReport.dataset_grain == "national_daily")
            .order_by(DailyReport.report_date)
        ).mappings().all()

        if not versions:
            raise ValueError("No canonical daily records found")

        if any(
            row["quality_status"] != "validated"
            for row in versions
        ):
            raise ValueError("A canonical version is not validated")

        dates = [row["report_date"] for row in versions]
        if len(set(dates)) != len(dates):
            raise ValueError("Duplicate canonical operational dates")

        version_ids = [row["version_id"] for row in versions]

        print(f"Canonical dates: {len(versions)}", flush=True)

        links = defaultdict(set)

        for version_id, source_id in session.execute(
            select(
                VersionSource.version_id,
                VersionSource.source_id,
            ).where(VersionSource.version_id.in_(version_ids))
        ):
            links[version_id].add(source_id)

        source_ids = set().union(*links.values())

        sources = session.execute(
            select(
                SourceDocument.id,
                SourceDocument.original_url,
                SourceDocument.sha256,
                SourceDocument.original_filename,
                SourceDocument.category,
                SourceDocument.size_bytes,
                SourceDocument.retrieved_at,
                SourceDocument.published_at,
                SourceDocument.storage_key,
            )
            .where(SourceDocument.id.in_(sorted(source_ids)))
            .order_by(SourceDocument.original_url, SourceDocument.sha256)
        ).mappings().all()

        source_map = {row["id"]: row for row in sources}

        if set(source_map) != source_ids:
            raise ValueError("Missing registered source metadata")

        queries = []

        for table in TABLES:
            queries.append(
                select(
                    table.version_id,
                    table.metric,
                    table.unit,
                    table.value,
                    table.zone,
                    table.period,
                    table.source_id,
                    table.source_page,
                    table.raw_text,
                ).where(table.version_id.in_(version_ids))
            )

        print("Reading canonical measurements...", flush=True)
        measurements = session.execute(
            union_all(*queries)
        ).mappings().all()

    # All database reads above used the same read-only snapshot.
    daily = {}
    for version in versions:
        version_id = version["version_id"]

        if not links[version_id]:
            raise ValueError("Canonical version has no linked sources")

        daily[version_id] = {
            "operational_date": version["report_date"].isoformat(),
            "report_version_id": version_id,
            "quality_status": version["quality_status"],
            "parser_version": version["parser_version"],
            "available_at": string_value(version["available_at"]),
            "source_ids_json": json.dumps(sorted(links[version_id])),
            **{column: "" for column in COLUMNS.values()},
        }

    long_rows = []
    seen = set()

    for measurement in measurements:
        version_id = measurement["version_id"]
        metric = measurement["metric"]

        if metric not in COLUMNS or metric not in METRICS:
            raise ValueError(f"Unsupported export metric: {metric}")

        _, unit, period, _ = METRICS[metric]

        if (
            measurement["unit"] != unit
            or measurement["period"] != period
            or measurement["zone"] != "national"
        ):
            raise ValueError(f"Unexpected dimensions for {metric}")

        key = (version_id, metric)
        if key in seen:
            raise ValueError(f"Duplicate canonical measurement: {metric}")
        seen.add(key)

        source_id = measurement["source_id"]
        if source_id not in links[version_id]:
            raise ValueError("Measurement source is not linked to its version")

        value = measurement["value"]
        if value is not None and not value.is_finite():
            raise ValueError("Non-finite measurement")

        daily[version_id][COLUMNS[metric]] = string_value(value)

        long_rows.append({
            "operational_date": daily[version_id]["operational_date"],
            "report_version_id": version_id,
            "metric": metric,
            "value": string_value(value),
            "unit": unit,
            "zone": measurement["zone"],
            "period": period,
            "source_id": source_id,
            "source_url": source_map[source_id]["original_url"],
            "source_sha256": source_map[source_id]["sha256"],
            "source_page": string_value(measurement["source_page"]),
            "raw_text": string_value(measurement["raw_text"]),
        })

    daily_rows = list(daily.values())
    long_rows.sort(
        key=lambda row: (row["operational_date"], row["metric"])
    )

    for row in daily_rows:
        for column in (
            "day_peak_generation_mw",
            "evening_peak_generation_mw",
            "maximum_generation_mw",
            "energy_generated_million_kwh",
        ):
            if row[column] == "":
                raise ValueError(f"Missing core measurement: {column}")

    source_fields = [
        "id",
        "original_url",
        "sha256",
        "original_filename",
        "category",
        "size_bytes",
        "retrieved_at",
        "published_at",
        "storage_key",
    ]
    source_rows = [
        {
            field: string_value(source[field])
            for field in source_fields
        }
        for source in sources
    ]

    daily_fields = [
        "operational_date",
        "report_version_id",
        "quality_status",
        "parser_version",
        "available_at",
        "source_ids_json",
        *COLUMNS.values(),
    ]
    measurement_fields = [
        "operational_date",
        "report_version_id",
        "metric",
        "value",
        "unit",
        "zone",
        "period",
        "source_id",
        "source_url",
        "source_sha256",
        "source_page",
        "raw_text",
    ]

    files = {
        "master_daily.csv": csv_bytes(daily_fields, daily_rows),
        "master_measurements.csv": csv_bytes(
            measurement_fields, long_rows
        ),
        "master_sources.csv": csv_bytes(
            source_fields, source_rows
        ),
    }

    present_dates = set(dates)
    missing_dates = []
    current = dates[0]

    while current <= dates[-1]:
        if current not in present_dates:
            missing_dates.append(current.isoformat())
        current += timedelta(days=1)

    created_at = datetime.now(timezone.utc)
    metadata = {
        "created_at": created_at.isoformat(),
        "dataset_checksum": hashlib.sha256(
            files["master_daily.csv"]
        ).hexdigest(),
        "scope": "Supported canonical Page 1 national measurements",
        "daily_rows": len(daily_rows),
        "measurement_rows": len(long_rows),
        "source_rows": len(source_rows),
        "earliest_operational_date": dates[0].isoformat(),
        "latest_operational_date": dates[-1].isoformat(),
        "member_version_ids": version_ids,
        "files": {
            name: {
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            }
            for name, data in files.items()
        },
        "metrics": {
            metric: {
                "column": column,
                "unit": METRICS[metric][1],
                "present_rows": sum(
                    row[column] != "" for row in daily_rows
                ),
                "missing_rows": sum(
                    row[column] == "" for row in daily_rows
                ),
            }
            for metric, column in COLUMNS.items()
        },
        "missing_canonical_dates_between_bounds": missing_dates,
        "limitations": [
            "This is the initial Page 1 national dataset.",
            "Missing canonical dates are not proof of missing official reports.",
            "Blank fields represent unavailable measurements, not zeros.",
            "Unknown availability timestamps remain blank.",
            "No claim of complete archive or variable coverage.",
        ],
    }

    output = (
        PROJECT_ROOT
        / "data"
        / "exports"
        / (
            "master_"
            + created_at.strftime("%Y%m%dT%H%M%SZ")
            + "_"
            + uuid4().hex[:8]
        )
    )
    output.mkdir(parents=True, exist_ok=False)

    for name, data in files.items():
        (output / name).write_bytes(data)

    # Written last to mark a completed export.
    (output / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "status": "exported",
        "daily_rows": len(daily_rows),
        "measurement_rows": len(long_rows),
        "source_rows": len(source_rows),
        "missing_canonical_dates": len(missing_dates),
        "dataset_checksum": metadata["dataset_checksum"],
        "output_folder": str(output),
    }, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())