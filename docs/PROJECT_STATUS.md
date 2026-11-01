# Project status — November 1, 2026

## Completed infrastructure

- Official BPDB PDF discovery, historical collection and incremental daily collection.
- Supported legacy/modern Page 1 national extraction, validation and quarantine.
- Neon source registration, measurement staging, consistency verification and canonical promotion.
- Database-derived master exports with checksums and source lineage.
- Google Drive recent-file/checkpoint push and checksum-verified restore.
- GitHub Actions Windows worker; noon Asia/Dhaka target via `0 6 * * *`.
- Successful manual hosted run and successful scheduled run 41305575589 on November 1.
  That scheduled run started at 12:15 UTC (18:15 Bangladesh); exact noon is not guaranteed.
- Foundation and backend CI passed on the previous main commit 87116482.

## This update: data-management API

- Protected `/api/v1/dataset/summary`, `/api/v1/collection/runs`, `/api/v1/dataset/daily`.
- Current validated national records only, inclusive date filters and bounded pagination.
- Exact decimal strings, null preservation, source URLs/checksums, version and metric provenance.
- Request-scoped PostgreSQL read-only repeatable-read transaction with a 15-second statement limit.
- Generic database failures and whitelisted worker counters; private storage paths are not returned.
- `/api/v1/system` now identifies implemented parser/scheduler capabilities, not live run health.
- API usage and local acceptance instructions: `docs/MONITORING_API.md`.

## Evidence and limits

- Last user-verified Neon snapshot: 2,379 canonical dates, 16,871 measurements;
  October 19, 2019–October 28, 2026; 188 calendar gaps. Not a fresh database query.
- Earlier full-batch verification matched all 2,378 versions and 16,858 measurements without issues;
  one subsequent daily promotion added one date and 13 measurements.
- This update: backend Ruff, compilation and dependency checks passed; pytest: 42 passed,\n  1 PostgreSQL integration test skipped, 1 upstream TestClient deprecation warning.
  See the commit's CI for hosted verification. A dedicated PostgreSQL integration test remains
  opt-in; SQLite tests do not establish production locking or transaction behavior.
- Monitoring had already been verified locally by the user (34 passed, 1 skipped).
  The current implementation is now included in the repository; new endpoints still require
  authenticated live Neon acceptance after pulling this update.
- No analytics, model evaluation, research findings or thesis report generator are claimed complete.

## Next milestone

Complete local browser acceptance of the real-data management frontend and CSV download.
Then choose compatible API hosting and deploy the API/frontend before moving to the
full-history data-quality audit and analytical/model development.


## Website update — November 1, 2026

- Real-data Overview, Collection History, Master Dataset and Data Quality pages implemented.
- Server-only API access, signed administrator sessions, sign-out and safe source links.
- Date filters, bounded pagination, metric-column selection and expandable source evidence.
- Complete filtered long-format CSV download from one backend snapshot, with provenance.
- Recent-sample metric availability is separate from whole-history calendar coverage.
- Frontend tests, TypeScript and production build passed; backend 44 passed, 1 skipped.
- Browser QA unavailable due to preview service/Next.js CLI incompatibility. No live Neon
  acceptance or website/API deployment was performed for this update.
- Next: local authenticated desktop/mobile acceptance, then compatible API hosting and Vercel
  deployment. After that, complete the full-history data-quality audit before analytics/models.
- See WEB_WORKSPACE.md for private configuration, commands, CSV semantics and acceptance checks.


## Values-only daily CSV update

- Main website CSV: one date per row, 13 stable metric headings with units, only dates and
  numeric/blank cells. Source-evidence CSV remains a separate detailed download.
- Date filters, chronological order, canonical-only selection and exact values are preserved.
- Missing values remain blank; redundant fractional zeroes are removed without float conversion.
- New tests cover headers, daily pivot, precision, zero/null distinction and dimension safeguards.
- Local/live Neon acceptance of the new file format remains required after restarting servers.


## Vercel deployment preparation
- Two projects from one repository: backend FastAPI and frontend Next.js.
- Python 3.12 pin, API 60-second function configuration and frontend export duration.
- Explicit hosted CSV size guard to avoid oversized function responses.
- Existing GitHub Actions worker, Neon data and Drive persistence retained.
- Actual Vercel import, private environment configuration and live acceptance remain pending.
- Follow VERCEL_DEPLOYMENT.md; hosting is not marked complete by code preparation.


## Full-history quality reporting — November 1, 2026
- User reports the API and website are live on Vercel; production URLs were not independently inspected.
- Added authenticated /api/v1/dataset/quality using all current validated national records.
- Calendar coverage by year, full-history/year-selected metric availability, explicit zero counts,
  first/last non-null bounds and paginated inclusive gap ranges.
- Replaced the previous latest-100-date sample; no source-gap cause is inferred.
- Local tests: 57 backend passed, 1 PostgreSQL integration skipped; 4 frontend tests passed.
  TypeScript, Next.js build, Ruff, Python compilation and dependency checks passed.
- Live acceptance of this endpoint/page remains pending after both Vercel deployments.
- Next: investigate gaps, unavailable fields and original-source agreement before research modelling.
- Definitions and acceptance: DATA_QUALITY.md.
