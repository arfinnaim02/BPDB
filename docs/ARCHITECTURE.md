# BPDB Intelligence — architecture decision record

## Day 1 scope

One repository; Next.js App Router/TypeScript/Tailwind frontend, FastAPI/Pydantic backend,
SQLAlchemy 2 + psycopg 3, Alembic and Neon PostgreSQL. Python 3.12. All source data must
come from verified official documents. SQLite is used only for isolated unit tests;
it is not a replacement for Neon. Frontend fetches public health endpoints server-side.
Administrative secrets never belong in NEXT_PUBLIC variables.

The backend and frontend run as separate processes. Ingestion will run in a separate
worker process rather than a long-running web request. The 12:00 Asia/Dhaka schedule,
persistent object storage, model runner and report queue are not implemented in Day 1.
Later analytics, ML, decisions and reporting directories will be added with real modules,
not empty scaffolding. shadcn/ui, ECharts and Lucide arrive with the dashboard phase.

## Core relational schema — implemented

| Table | Grain and ownership |
|---|---|
| ingestion_runs | One collection attempt; trigger, status, times, counts, sanitized error code |
| source_documents | One original URL/content-checksum pair; provenance, raw storage key, retrieval time |
| daily_reports | Unique operational date + dataset grain; one nullable canonical version pointer |
| daily_report_versions | One immutable logical extraction revision; quality, parser, availability, reason |
| version_sources | Many-to-many membership: several original report categories can support one version |
| extraction_issues | Source/version-specific validation issue with details and resolution timestamp |
| generation_observations | Version, metric, zone, period, unit |
| demand_observations | Version, metric, zone, period, unit |
| fuel_observations | Version, metric, zone, period, unit, fuel |
| cost_observations | Version, metric, zone, period, unit, fuel (all = national total) |
| load_shedding_observations | Version, metric, zone, period, unit |
| dataset_versions | Frozen member version IDs, cutoff, export checksum and row count |

Values use Numeric(24,6), not binary floating point. Units remain source-specific;
normalization will be a separately documented transformation. Missing value = NULL,
not zero. Observation rows carry source ID, source page and raw text where available.
Production costs have their own table so national cost is not duplicated into fuel rows.
Report date is an operational date confirmed from PDF content, not an archive date hint.

The composite canonical foreign key ensures the pointed-to version belongs to that
same report. The initial migration creates that circular foreign key after both tables.
The migration is frozen and does not import the changing ORM metadata.

## Canonical promotion rules

1. Preserve every distinct original document; never overwrite PDF bytes.
2. Deduplicate exact URL/checksum pairs with a database unique constraint.
3. Create or locate a report by unique (report_date, dataset_grain).
4. Lock the report row inside the caller's transaction before changing its pointer.
5. Only a validated extraction may be promoted; incomplete/conflicting input cannot replace it.
6. Repeating promotion to the same version is a no-op.
7. A correction requires an explicit verified-correction flag, reason and increasing version number.
8. Preserve the old extraction, observation rows and source membership after promotion.
9. Any failure rolls back the whole transaction.

Day 1 implements the promotion primitive and schema; it does not implement a complete
collector, validator, reviewer or immutable-row permissions. The ingestion service must
handle unique-insert races by rolling back/reloading, acquire a run-level advisory lock,
and enforce consistent source membership before invoking promotion. Concurrent PostgreSQL
promotion is not yet integration-tested.

## Planned schema additions, introduced with their owning modules

| Table | Planned key, relationships, required lineage |
|---|---|
| monthly_aggregates | Unique dataset_version_id + month + metric + zone + fuel + unit; coverage count and eligibility flag |
| model_experiments | Dataset FK, target, horizon, availability policy, feature definition, seed, fold windows, parameters and metrics |
| model_versions | Experiment FK, artifact checksum/key, code revision, trained-through date |
| forecast_runs | Model + dataset FKs, forecast origin, generated time, horizon, outputs and intervals |
| decision_scenarios | Dataset/forecast FKs, assumptions, scenario parameters, evidence, limitations |
| report_jobs | Frozen dataset FK, selected modules, filters, status, requested time |
| report_artifacts | Job FK, model references, storage key, checksum, created time |

Dataset membership JSON is an initial frozen manifest. A relational membership table is
recommended before large-scale model/report workloads. An export's checksum must include
an explicitly defined stable serialization. No export is created in Day 1.

## Operational design to implement

- Daily worker at noon Dhaka (06:00 UTC), overlap scan, bounded retries and monitoring.
- PDFs stored by date/type/content hash in persistent object storage.
- Master CSV is derived only from canonical database rows within a frozen snapshot.
- Forecast training uses as-of availability and chronological folds; no future features.
- Readiness checks both connectivity and the expected migration revision.
- Production logs use safe codes; connection errors are not sent to clients.
- Manual collection/training controls require authentication and future rate limiting.
- Before deployment: separate migration/runtime roles, database backup/recovery drill,
  HTTPS, platform secret management and protected or disabled API documentation.

## Source references checked during foundation

- Official archive: https://misc.bpdb.gov.bd/daily-generation-archive
- Indexed official page listing categories: https://misc.bpdb.gov.bd/daily-generation-archive?page=24
- FastAPI settings: https://fastapi.tiangolo.com/advanced/settings/
- SQLAlchemy 2 PostgreSQL driver: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
- Next.js installation: https://nextjs.org/docs/app/getting-started/installation

The live archive request returned 503 in this environment. Search-index page text supports
the category names only; it does not verify source HTML, PDFs, measurements or publication lag.
