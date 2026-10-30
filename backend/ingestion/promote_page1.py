"""Promote verified Page 1 versions without replacing existing canonicals."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

from app.db.models import (
    DailyReport,
    IngestionRun,
    ReportVersion,
    VersionSource,
)
from app.db.session import session_factory
from sqlalchemy import case, literal, select, text, union_all, update

from ingestion.import_page1_measurements import (
    EXTRACTION_ROOT,
    METRICS,
    TABLES,
    load_group,
    preload_registered_sources,
)
from ingestion.register_page1_sources import DEFAULT_BATCH, prepare_sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit must be zero or positive")

    batch_root = EXTRACTION_ROOT / DEFAULT_BATCH
    verification = json.loads(
        (
            batch_root / "validation" / "database_verification.json"
        ).read_text(encoding="utf-8")
    )

    if (
        verification["status"] != "passed"
        or verification["batch"] != DEFAULT_BATCH
        or verification["issue_count"] != 0
    ):
        raise ValueError("A passing database verification is required")

    print("Checking source files and eligible records...", flush=True)
    groups, _ = prepare_sources(batch_root)
    groups.sort(key=lambda group: group["operational_date"])
    selected = groups[:args.limit] if args.limit else groups

    plans = [
        (group, load_group(batch_root, group))
        for group in selected
    ]
    if not plans:
        raise ValueError("No eligible dates selected")

    parser_key = "page1:" + DEFAULT_BATCH
    selected_dates = {
        group["operational_date"] for group, _ in plans
    }

    from datetime import date
    from decimal import Decimal

    factory = session_factory()

    with factory.begin() as session:
        if args.apply:
            session.execute(text(
                "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"
            ))
        else:
            session.execute(text(
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
            ))

        source_ids = preload_registered_sources(session, plans)

        statement = (
            select(
                ReportVersion.id.label("version_id"),
                ReportVersion.report_id,
                ReportVersion.quality_status,
                DailyReport.report_date,
                DailyReport.current_version_id,
            )
            .join(
                DailyReport,
                DailyReport.id == ReportVersion.report_id,
            )
            .where(
                ReportVersion.parser_version == parser_key,
                DailyReport.dataset_grain == "national_daily",
                DailyReport.report_date.in_([
                    date.fromisoformat(day)
                    for day in sorted(selected_dates)
                ]),
            )
            .order_by(DailyReport.report_date)
        )

        if args.apply:
            statement = statement.with_for_update(
                of=[DailyReport, ReportVersion]
            )

        rows = session.execute(statement).all()
        by_date = defaultdict(list)

        for row in rows:
            by_date[row.report_date.isoformat()].append(row)

        if len(rows) != len(plans):
            raise ValueError("Unexpected staged-version count")

        version_ids = [row.version_id for row in rows]

        links = defaultdict(set)
        for version_id, source_id in session.execute(
            select(
                VersionSource.version_id,
                VersionSource.source_id,
            ).where(VersionSource.version_id.in_(version_ids))
        ):
            links[version_id].add(source_id)

        queries = []
        for table in TABLES:
            fuel = table.fuel if hasattr(table, "fuel") else literal(None)
            queries.append(
                select(
                    table.version_id,
                    literal(table.__tablename__),
                    table.metric,
                    table.unit,
                    table.value,
                    table.zone,
                    table.period,
                    fuel,
                    table.source_id,
                    table.source_page,
                    table.raw_text,
                ).where(table.version_id.in_(version_ids))
            )

        actual = defaultdict(Counter)
        for row in session.execute(union_all(*queries)):
            actual[row[0]][tuple(row)[1:]] += 1

        pending = {}
        already_current = 0

        for group, records in plans:
            day = group["operational_date"]
            matches = by_date.get(day, [])

            if len(matches) != 1:
                raise ValueError(f"Ambiguous staged version: {day}")

            row = matches[0]

            if row.quality_status not in ("partial", "validated"):
                raise ValueError(f"Version is not eligible: {day}")

            if row.current_version_id not in (None, row.version_id):
                raise ValueError(
                    f"Another canonical version exists: {day}. "
                    "Correction review is required."
                )

            expected_links = {
                source_ids[(
                    record["source_url"],
                    record["source_sha256"],
                )]
                for record in records
            }
            if links[row.version_id] != expected_links:
                raise ValueError(f"Source-link mismatch: {day}")

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

            if actual[row.version_id] != expected:
                raise ValueError(f"Measurement mismatch: {day}")

            if row.current_version_id == row.version_id:
                if row.quality_status != "validated":
                    raise ValueError(
                        f"Canonical version has unexpected status: {day}"
                    )
                already_current += 1
            else:
                pending[row.report_id] = row.version_id

        result = {
            "stage": "page1_canonical_promotion",
            "batch": DEFAULT_BATCH,
            "selected_dates": len(plans),
            "already_canonical": already_current,
            "eligible_for_promotion": len(pending),
            "promoted": 0,
            "scope": "Supported Page 1 national metrics",
        }

        if args.apply and pending:
            session.execute(
                update(ReportVersion)
                .where(
                    ReportVersion.id.in_(list(pending.values())),
                    ReportVersion.quality_status == "partial",
                )
                .values(quality_status="validated")
                .execution_options(synchronize_session=False)
            )

            changed = session.execute(
                update(DailyReport)
                .where(
                    DailyReport.id.in_(list(pending)),
                    DailyReport.current_version_id.is_(None),
                )
                .values(
                    current_version_id=case(
                        pending,
                        value=DailyReport.id,
                    )
                )
                .execution_options(synchronize_session=False)
            )

            if changed.rowcount != len(pending):
                raise ValueError("Canonical update count mismatch")

            result["promoted"] = changed.rowcount

        if args.apply:
            session.add(IngestionRun(
                trigger="manual",
                status="succeeded",
                finished_at=datetime.now(timezone.utc),
                statistics=dict(result),
            ))

    # Printed only after a successful transaction commit.
    result["mode"] = "applied" if args.apply else "preview"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())