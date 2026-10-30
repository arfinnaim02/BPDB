"""Read-only verification of staged Page 1 measurements against local records."""

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

from app.db.models import DailyReport, ReportVersion, VersionSource
from app.db.session import session_factory
from sqlalchemy import literal, select, text, union_all

from ingestion.import_page1_measurements import (
    EXTRACTION_ROOT,
    METRICS,
    TABLES,
    load_group,
    preload_registered_sources,
)
from ingestion.register_page1_sources import (
    DEFAULT_BATCH,
    prepare_sources,
)


def main():
    batch_root = EXTRACTION_ROOT / DEFAULT_BATCH
    parser_key = "page1:" + DEFAULT_BATCH

    print("Checking original files and extraction records...", flush=True)
    groups, _ = prepare_sources(batch_root)
    groups.sort(key=lambda group: group["operational_date"])

    plans = [
        (group, load_group(batch_root, group))
        for group in groups
    ]

    expected_measurements = sum(
        len(records[0]["extraction"]["observations"])
        for _, records in plans
    )

    issues = []
    expected_dates = {
        group["operational_date"] for group, _ in plans
    }

    factory = session_factory()

    with factory() as session:
        # Keep all database checks on one read-only snapshot.
        session.execute(text(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
        ))
        source_ids = preload_registered_sources(session, plans)

        print("Reading staged versions...", flush=True)
        version_rows = session.execute(
            select(
                ReportVersion.id,
                ReportVersion.quality_status,
                DailyReport.report_date,
                DailyReport.current_version_id,
            )
            .join(DailyReport, DailyReport.id == ReportVersion.report_id)
            .where(
                ReportVersion.parser_version == parser_key,
                DailyReport.dataset_grain == "national_daily",
            )
        ).all()

        versions_by_date = defaultdict(list)
        for version in version_rows:
            versions_by_date[version.report_date.isoformat()].append(
                version
            )

        print("Reading source links...", flush=True)
        links = defaultdict(set)

        for version_id, source_id in session.execute(
            select(VersionSource.version_id, VersionSource.source_id)
            .join(
                ReportVersion,
                ReportVersion.id == VersionSource.version_id,
            )
            .where(ReportVersion.parser_version == parser_key)
        ):
            links[version_id].add(source_id)

        print("Reading measurement tables...", flush=True)
        queries = []

        for table in TABLES:
            fuel = (
                table.fuel
                if hasattr(table, "fuel")
                else literal(None)
            )
            queries.append(
                select(
                    table.version_id.label("version_id"),
                    literal(table.__tablename__).label("table_name"),
                    table.metric,
                    table.unit,
                    table.value,
                    table.zone,
                    table.period,
                    fuel.label("fuel"),
                    table.source_id,
                    table.source_page,
                    table.raw_text,
                )
                .join(
                    ReportVersion,
                    ReportVersion.id == table.version_id,
                )
                .where(ReportVersion.parser_version == parser_key)
            )

        actual_measurements = defaultdict(Counter)
        actual_count = 0

        for row in session.execute(union_all(*queries)):
            actual_measurements[row.version_id][tuple(row)[1:]] += 1
            actual_count += 1

        print("Comparing values, dimensions and provenance...", flush=True)

        for group, records in plans:
            day = group["operational_date"]
            versions = versions_by_date.get(day, [])

            if len(versions) != 1:
                issues.append({
                    "date": day,
                    "code": "unexpected_version_count",
                    "count": len(versions),
                })
                continue

            version = versions[0]

            if version.quality_status not in ("partial", "validated"):
                issues.append({
                    "date": day,
                    "code": "unexpected_quality_status",
                })

            if version.current_version_id not in (None, version.id):
                issues.append({
                    "date": day,
                    "code": "different_canonical_version_exists",
                })

            expected_links = {
                source_ids[(
                    record["source_url"],
                    record["source_sha256"],
                )]
                for record in records
            }

            if links[version.id] != expected_links:
                issues.append({
                    "date": day,
                    "code": "source_link_mismatch",
                })

            primary = records[0]
            primary_id = source_ids[(
                primary["source_url"],
                primary["source_sha256"],
            )]

            expected = Counter()

            for observation in primary["extraction"]["observations"]:
                table, unit, period, dimensions = METRICS[
                    observation["metric"]
                ]

                from decimal import Decimal

                expected[(
                    table.__tablename__,
                    observation["metric"],
                    unit,
                    Decimal(observation["value"]),
                    "national",
                    period,
                    dimensions.get("fuel"),
                    primary_id,
                    observation["source_page"],
                    observation["raw_text"],
                )] += 1

            if actual_measurements[version.id] != expected:
                issues.append({
                    "date": day,
                    "code": "measurement_or_provenance_mismatch",
                })

        extra_dates = set(versions_by_date) - expected_dates
        for day in sorted(extra_dates):
            issues.append({
                "date": day,
                "code": "unexpected_database_date",
            })

    if len(version_rows) != len(plans):
        issues.append({"code": "total_version_count_mismatch"})

    if actual_count != expected_measurements:
        issues.append({"code": "total_measurement_count_mismatch"})

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "batch": DEFAULT_BATCH,
        "status": "passed" if not issues else "failed",
        "expected_versions": len(plans),
        "database_versions": len(version_rows),
        "expected_measurements": expected_measurements,
        "database_measurements": actual_count,
        "issue_count": len(issues),
        "issues": issues,
        "scope": (
            "Database consistency with current eligible Page 1 extraction; "
            "not proof of complete historical coverage."
        ),
    }

    destination = batch_root / "validation" / "database_verification.json"
    destination.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2))
    print(f"\nVerification report: {destination}")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())