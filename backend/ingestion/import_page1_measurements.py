"""Import eligible Page 1 measurements as staged report versions.

Default: preview only.
--apply: write measurements, without canonical promotion.
"""

import argparse
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import (
    CostObservation,
    DailyReport,
    DemandObservation,
    EnvironmentObservation,
    FuelObservation,
    GenerationObservation,
    IngestionRun,
    ReportVersion,
    SourceDocument,
    VersionSource,
)
from app.db.session import session_factory
from sqlalchemy import func, select, text, tuple_

from ingestion.register_page1_sources import (
    DEFAULT_BATCH,
    prepare_sources,
)
from ingestion.validate_page1 import check_record

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXTRACTION_ROOT = PROJECT_ROOT / "data" / "processed" / "page1_extraction"

# metric: (table, required unit, period, additional dimensions)
METRICS = {
    "day_peak_generation": (
        GenerationObservation, "MW", "day_peak", {}
    ),
    "evening_peak_generation": (
        GenerationObservation, "MW", "evening_peak", {}
    ),
    "minimum_generation": (
        GenerationObservation, "MW", "daily_minimum", {}
    ),
    "maximum_generation": (
        GenerationObservation, "MW", "daily_maximum", {}
    ),
    "energy_generated": (
        GenerationObservation, "million_kWh", "daily", {}
    ),
    "day_peak_demand": (
        DemandObservation, "MW", "day_peak", {}
    ),
    "evening_peak_demand": (
        DemandObservation, "MW", "evening_peak", {}
    ),
    "energy_demand": (
        DemandObservation, "million_kWh", "daily", {}
    ),
    "energy_unserved": (
        DemandObservation, "million_kWh", "daily", {}
    ),
    "gas_supplied": (
        FuelObservation, "MMCFD", "daily", {"fuel": "gas"}
    ),
    "production_cost_per_kwh": (
        CostObservation, "BDT/kWh", "daily", {"fuel": "all"}
    ),
    "total_production_cost": (
        CostObservation, "BDT", "daily", {"fuel": "all"}
    ),
    "maximum_temperature": (
        EnvironmentObservation, "degC", "daily_maximum", {}
    ),
}

TABLES = (
    GenerationObservation,
    DemandObservation,
    FuelObservation,
    CostObservation,
    EnvironmentObservation,
)


def measurement_signature(observations):
    return sorted(
        (
            item["metric"],
            item["unit"],
            Decimal(item["value"]),
        )
        for item in observations
    )


def load_group(batch_root, group):
    records = []

    for source in sorted(group["sources"], key=lambda item: item["url"]):
        path = batch_root / source["record_path"].replace("\\", "/")
        record = json.loads(path.read_text(encoding="utf-8"))

        if (
            record["batch_status"] != "extracted"
            or record["source_url"] != source["url"]
            or record["source_sha256"] != source["sha256"]
            or record["extraction"]["operational_date"]
            != group["operational_date"]
            or record["extraction"]["issues"]
        ):
            raise ValueError("Source/extraction reference mismatch")

        if check_record(record):
            raise ValueError(
                f"Record no longer passes validation: {source['url']}"
            )

        observations = record["extraction"]["observations"]
        seen = set()

        for observation in observations:
            metric = observation["metric"]
            if metric not in METRICS or metric in seen:
                raise ValueError(f"Unknown or duplicate metric: {metric}")
            seen.add(metric)

            _, expected_unit, _, _ = METRICS[metric]
            if observation["unit"] != expected_unit:
                raise ValueError(f"Unexpected unit for {metric}")

            value = Decimal(observation["value"])
            if not value.is_finite():
                raise ValueError(f"Non-finite value for {metric}")

            # Prevent silent rounding by Numeric(24, 6).
            if value != value.quantize(Decimal("0.000001")):
                raise ValueError(f"More than six decimal places: {metric}")
            if abs(value) >= Decimal("1000000000000000000"):
                raise ValueError(f"Value exceeds database precision: {metric}")

        records.append(record)

    if not records:
        raise ValueError("Empty source group")

    if len({record["source_sha256"] for record in records}) != 1:
        raise ValueError("Different PDF revisions require separate review")

    expected = measurement_signature(
        records[0]["extraction"]["observations"]
    )
    if any(
        measurement_signature(record["extraction"]["observations"])
        != expected
        for record in records[1:]
    ):
        raise ValueError("Identical-source group has conflicting extraction")

    return records


def preload_registered_sources(session, plans):
    keys = sorted({
        (record["source_url"], record["source_sha256"])
        for _, records in plans
        for record in records
    })

    source_ids = {}

    # Bound each database statement rather than waiting indefinitely.
    session.execute(text("SET LOCAL statement_timeout = '60000'"))

    for offset in range(0, len(keys), 200):
        chunk = keys[offset:offset + 200]

        print(
            f"Checking Neon sources "
            f"{offset + 1}-{offset + len(chunk)}/{len(keys)}...",
            flush=True,
        )

        rows = session.execute(
            select(
                SourceDocument.id,
                SourceDocument.original_url,
                SourceDocument.sha256,
            ).where(
                tuple_(
                    SourceDocument.original_url,
                    SourceDocument.sha256,
                ).in_(chunk)
            )
        )

        for source_id, url, checksum in rows:
            source_ids[(url, checksum)] = source_id

        print(
            f"Registered sources found: {len(source_ids)}/{len(keys)}",
            flush=True,
        )

    missing = [key for key in keys if key not in source_ids]

    if missing:
        raise ValueError(
            f"{len(missing)} sources are not registered. "
            f"First missing URL: {missing[0][0]}"
        )

    return source_ids


def registered_sources(session, records):
    source_ids = session.info.get("registered_source_ids")

    if source_ids is None:
        raise RuntimeError("Registered-source cache was not loaded")

    sources = []

    for record in records:
        key = (record["source_url"], record["source_sha256"])
        source_id = source_ids.get(key)

        if source_id is None:
            raise ValueError(
                f"Source is not registered: {record['source_url']}"
            )

        # The importer only needs .id; avoid loading ORM objects again.
        sources.append(SimpleNamespace(id=source_id))

    return sources

def import_group(session, group, records, parser_key):
    day = date.fromisoformat(group["operational_date"])

    # Serialize concurrent imports for the same date.
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": f"bpdb:national_daily:{day.isoformat()}"},
    )

    sources = registered_sources(session, records)

    report = session.scalar(
        select(DailyReport)
        .where(
            DailyReport.report_date == day,
            DailyReport.dataset_grain == "national_daily",
        )
        .with_for_update()
    )

    if report is None:
        report = DailyReport(
            report_date=day,
            dataset_grain="national_daily",
        )
        session.add(report)
        session.flush()

    existing = session.scalar(
        select(ReportVersion).where(
            ReportVersion.report_id == report.id,
            ReportVersion.parser_version == parser_key,
        )
    )

    expected = measurement_signature(
        records[0]["extraction"]["observations"]
    )

    if existing is not None:
        linked = set(session.scalars(
            select(VersionSource.source_id).where(
                VersionSource.version_id == existing.id
            )
        ))
        actual = []

        for table in TABLES:
            rows = session.scalars(
                select(table).where(table.version_id == existing.id)
            )
            actual.extend(
                (row.metric, row.unit, row.value)
                for row in rows
            )

        if (
            linked != {source.id for source in sources}
            or sorted(actual) != expected
        ):
            raise ValueError("Existing version differs; review required")

        return "existing", 0

    previous_number = session.scalar(
        select(func.max(ReportVersion.version_number)).where(
            ReportVersion.report_id == report.id
        )
    ) or 0

    version = ReportVersion(
        report_id=report.id,
        version_number=previous_number + 1,
        quality_status="partial",
        parser_version=parser_key,
        available_at=None,
    )
    session.add(version)
    session.flush()

    for source in sources:
        session.add(VersionSource(
            version_id=version.id,
            source_id=source.id,
        ))

    # Identical PDF copies share one measurement set.
    primary_source = sources[0]
    observations = records[0]["extraction"]["observations"]

    for observation in observations:
        table, unit, period, dimensions = METRICS[observation["metric"]]

        session.add(table(
            version_id=version.id,
            source_id=primary_source.id,
            metric=observation["metric"],
            zone="national",
            period=period,
            value=Decimal(observation["value"]),
            unit=unit,
            source_page=observation["source_page"],
            raw_text=observation["raw_text"],
            **dimensions,
        ))

    session.flush()
    return "inserted", len(observations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit must be zero or positive")

    batch_root = EXTRACTION_ROOT / args.batch

    # Recheck original PDF checksums using the registration preflight.
    print(
        "Step 1: checking local PDF checksums and source references...",
        flush=True,
    )
    groups, _ = prepare_sources(batch_root)

    print(
        f"Local source checks complete: {len(groups)} eligible dates.",
        flush=True,
    )
    groups.sort(key=lambda group: group["operational_date"])
    selected = groups[:args.limit] if args.limit else groups

    plans = [
        (group, load_group(batch_root, group))
        for group in selected
    ]
    parser_key = "page1:" + args.batch

    factory = session_factory()

    print(
        f"Local checks complete for {len(plans)} dates. "
        "Checking registered sources in Neon...",
        flush=True,
    )

    # Read-only database preflight before creating an ingestion run.
    with factory() as session:
        source_ids = preload_registered_sources(session, plans)

    print(
        f"Neon preflight complete: {len(source_ids)} sources verified.",
        flush=True,
    )

    planned_measurements = sum(
        len(records[0]["extraction"]["observations"])
        for _, records in plans
    )

    print(f"Selected dates: {len(plans)}")
    print(f"Measurement rows before existing-version checks: {planned_measurements}")

    if not args.apply:
        print("Preview complete. No database changes made.")
        return 0

    if not plans:
        raise ValueError("No dates selected")

    run_id = str(uuid4())
    statistics = {
        "stage": "page1_measurement_staging",
        "batch": args.batch,
        "inserted_versions": 0,
        "existing_versions": 0,
        "inserted_measurements": 0,
        "canonical_records_promoted": 0,
    }

    with factory.begin() as session:
        session.add(IngestionRun(
            id=run_id,
            trigger="manual",
            status="running",
            statistics=dict(statistics),
        ))

    failure = None
    failed_date = None

    for index, (group, records) in enumerate(plans, 1):
        try:
            with factory.begin() as session:
                session.info["registered_source_ids"] = source_ids
                session.execute(
                    text("SET LOCAL statement_timeout = '60000'")
                )
                status, count = import_group(
                    session, group, records, parser_key
                )

            statistics[f"{status}_versions"] += 1
            statistics["inserted_measurements"] += count

            print(
                f"Date {index}/{len(plans)} "
                f"{group['operational_date']}: {status}",
                flush=True,
            )
        except Exception as exc:
            failure = type(exc).__name__
            failed_date = group["operational_date"]
            break

    with factory.begin() as session:
        run = session.get(IngestionRun, run_id)
        run.status = (
            "succeeded"
            if failure is None
            else (
                "partial"
                if statistics["inserted_versions"]
                else "failed"
            )
        )
        run.finished_at = datetime.now(timezone.utc)
        run.error_code = failure
        run.statistics = dict(statistics)

    print(json.dumps({
        "run_id": run_id,
        **statistics,
        "error_type": failure,
        "failed_date": failed_date,
    }, indent=2))

    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())