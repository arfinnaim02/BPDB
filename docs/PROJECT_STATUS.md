# Project status — 2026-10-25

**Day 1: implemented foundation; external acceptance gates remain pending.**
Do not label the complete Day 1 milestone accepted until Neon and actual BPDB discovery pass.

## Completed and checked

- Instructions compared: two identical master prompts.
- Local files audited; earlier shared Drive folder successfully accessed.
- Existing parser/collector, legacy 556-row CSV and selected forecasting modules reviewed.
  See EXISTING_CODE_AUDIT.md for exact scope, scale concerns and reuse decisions.
- Unified repository initialized; Python 3.12 and Node 24 environments used locally.
- FastAPI health/readiness endpoints, protected administrative status, CORS and secret settings.
- Twelve core SQLAlchemy tables and a frozen Alembic initial migration; PostgreSQL SQL emitted.
- Unique report/date/grain and source URL/checksum constraints; same-report canonical FK.
- Canonical promotion, correction safeguards and rollback behavior tested.
- Bounded source discovery, header-based categories, date hints, retry and failure handling.
- Legacy numeric helper adapted to strict exact Decimal parsing; missing values preserved.
- Minimal Next.js / TypeScript / Tailwind status screen built and connected to the actual API.
- Windows PowerShell installation/migration/test/start commands and environment examples.
- Architecture, data dictionary, source inventory, audit, known issues and checklist.
- Backend/frontend CI checks configured (not executed on GitHub).

## Validation observed

| Check | Result | Scope |
|---|---|---|
| pytest | 30 passed, 1 skipped | API, discovery, numeric parsing, constraints, promotion, transactions and SQL generation |
| Real PostgreSQL test | Skipped | No TEST_DATABASE_URL; not evidence of Neon compatibility |
| Ruff | Pass | Backend and runtime smoke script |
| Dependency consistency | Pass | pip check |
| PostgreSQL migration SQL | Generated and checked | 12 core tables + Alembic ledger and canonical FK; no live upgrade |
| Frontend TypeScript | Pass | npm run typecheck |
| Frontend production build | Pass | Next.js 16.4.3, React 19.3.1 |
| Runtime smoke check | Pass | Actual API and production frontend render health/readiness state |
| Live archive discovery CLI | Failed with HTTPStatusError | Earlier direct request returned 503; source compatibility remains unverified |
| Windows execution | Not performed | PowerShell commands supplied; local tests ran on Linux |

One upstream FastAPI/Starlette TestClient deprecation warning is recorded; no failed tests.
SQLite tests do not prove PostgreSQL row-lock behavior or production concurrency.
No original PDF has been independently checked and no model metric has been adopted.

## Created files

- backend/app/: configuration, database models/session, API and canonical promotion service.
- backend/ingestion/: discovery and numeric token helper.
- backend/alembic/, backend/alembic.ini: frozen initial migration and migration runner.
- backend/tests/: unit tests, synthetic HTML fixture and opt-in PostgreSQL integration test.
- backend/requirements*.txt, pyproject.toml: dependency bounds, tested pins and check settings.
- frontend/: minimal App Router health page, loading/error states, Tailwind and npm lockfile.
- scripts/smoke.py: temporary-process runtime integration check.
- docs/: architecture, audit, setup, schema SQL, dictionary and phase tracking.
- .env.example, .gitignore, .github/workflows/tests.yml, README.md.

## Blocked / next dependencies

1. User configures DATABASE_URL locally; run actual migration, Alembic check and readiness.
2. Run opt-in PostgreSQL test on a dedicated branch to verify migration and core constraints.
3. Obtain authentic archive HTML and representative PDFs; verify layouts, units and dates.
4. Reconcile the 22 apparent scale anomalies in the legacy dataset against original PDFs.
5. Adapt validated legacy parsing patterns, implement raw preservation, field evidence,
   quarantine/revision handling and transactional ingestion before any historical import.
6. Continue with the remaining phases below; none is represented as already implemented.
