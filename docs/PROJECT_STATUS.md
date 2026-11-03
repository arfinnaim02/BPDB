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


## Registered source audit — November 2, 2026
- Added protected /api/v1/dataset/audit and Data Quality → Investigate sources.
- Missing-date evidence links national report versions, Page 1 source metadata and safe issue codes.
- Archive hints remain possible matches, separate from operational-date-linked metadata.
- Undated held-source queue exposes registered quarantine/review states without assigning dates.
- Deterministic PDF comparison plan includes original links/checksums and canonical measurement evidence.
- No original PDFs were newly inspected, no verification result was certified, and no records were repaired.
- Local tests: 69 backend passed, 1 PostgreSQL test skipped; 4 frontend tests passed; TypeScript/build/lint
  and compilation/dependency checks passed. Production/browser acceptance remains pending.
- Definitions and live checks: SOURCE_AUDIT.md.


## Generation and demand analytics — November 2, 2026
- Added protected descriptive analytics API and Generation & demand website page.
- Inclusive date filters; daily/monthly/yearly observed series with source-record drill-down.
- Correct MW means versus observed energy sums, completeness labels and missing-value gaps.
- Daily descriptive statistics, availability counts and precise decimal tables.
- Parser-capability-aware metric descriptions, without date-based layout assumptions or imputation.
- Apache ECharts history chart; read-only analysis, no forecasts or data repairs.
- Local checks: 84 backend tests passed, 1 PostgreSQL integration skipped; 7 frontend tests,
  lint, compilation, dependencies, TypeScript and production build passed.
- Deployed chart/runtime acceptance and original-PDF verification remain separate checks.
- Methodology and acceptance: HISTORICAL_ANALYTICS.md.

## Measurement screening and research-readiness audit — November 2, 2026

- Added protected read-only `/api/v1/dataset/measurement-review` and `/quality/review`.
- Screens current national generation/energy measurements with explicit physical-bound
  tolerances, dimension/provenance checks and a labelled low-energy-ratio heuristic.
- Preserves flagged values, source/checksum/page/raw text, version links and pagination;
  it does not save review decisions, alter canonical data or certify unflagged records.
- Legacy parser v3 rejects split/malformed energy numeric prefixes instead of silently
  accepting their first digit. Already-linked historical records are not auto-repaired.
- A synthetic split-token regression reproduces the prior failure mode; this does not
  prove the cause of the 4 January 2020 energy=1 record. Its original PDF is unverified.
- Local checks: 103 backend tests passed, 1 PostgreSQL integration skipped; 7 frontend
  tests passed. TypeScript, production build, Ruff and Python compilation passed.
- Representative existing PDFs still extract 166.4 (30 November 2019 legacy) and
  324.38721 (27 October 2026 modern) million kWh. Not a measured accuracy estimate.
- Earlier analytics deployment was browser-verified for generation and energy. User
  screenshots subsequently show 2,383 canonical dates through 1 November 2026.
- Research protocol: `RESEARCH_READINESS.md`, including source verification, versioned
  corrections, immutable snapshots, target feasibility and leakage-safe evaluation.
- Pending: original-PDF confirmation, durable review ledger, reviewed historical repair,
  frozen research dataset, cost-target complete-month assessment and model experiments.
- This update's production/browser acceptance is separate from local CI; see final
  delivery notes for any live verification performed after deployment.

### Live acceptance and CI follow-up

- Production review screened 2,383 dates at approximately 23:00 Bangladesh time on
  2 November: 19 flagged dates, comprising 18 low-ratio heuristic dates and one minimum
  daily-energy bound warning (9 June 2026). These are not 19 confirmed errors.
- Browser-verified the full queue, source evidence expansion and inclusive 4 January
  2020 filter returning exactly one flagged date with the stored energy=1 evidence.
- Foundation CI exposed that its lightweight pinned environment lacks pdfplumber.
  Moved PDF-runtime import inside the file-opening function; text-only tests now run
  without that optional runtime. Both pinned-foundation and full-worker environments
  pass 103 tests, with one PostgreSQL integration skipped and one upstream warning.
- Neither the January source nor the June source has been independently PDF-verified.
  Canonical measurements remain unchanged; the remaining source-review gate is open.

## Historical comparison dashboard — November 2, 2026

- Added protected `/api/v1/analytics/comparisons` and `/analytics/comparisons`.
- Day/evening generation-demand timelines use identical matched daily observations;
  daily/monthly/yearly views, signed differences, coverage and source-record drill-down.
- Selected-year monthly profiles, year-by-month heatmap, exact monthly/year tables,
  correct observed energy sums and observation-weighted annual MW means.
- MoM/YoY changes require complete calendar months and nonzero baselines; otherwise
  explicit unavailable reasons are shown. Missing data remains null, and zero remains zero.
- Date filters, up to eight seasonal years, independent table pagination, zoom/legends,
  screen-warning counts and request fingerprints. Screening candidates remain included.
- Local checks: 117 backend tests passed, 1 PostgreSQL integration skipped; 11 frontend
  tests passed. Ruff, compilation, TypeScript and production build passed.
- Same 117 tests also pass in the pinned lightweight foundation environment.
- Production deployment and browser acceptance of this new dashboard are separate checks.
- Detailed formulas, scope, Windows commands and 12 manual tests: HISTORICAL_COMPARISONS.md.
- No models, forecasts, causal conclusions or source corrections were produced by this step.

### Live comparison acceptance

- Production loaded 2,383 paired evening-peak dates over 2,571 calendar days (92.69%)
  and preserved the 19 generation/energy screening candidates.
- Verified 1 November 2026: 16,103.76 MW generation, 16,325.68 MW demand and signed
  difference 221.92 MW, with a working source-record link showing the same master values.
- Verified legacy 4 January 2020 day-peak demand remains unavailable: zero matched days,
  null comparison values and the existing energy review warning; energy units remain separate.
- The live Reset test exposed stale uncontrolled form selections after client navigation.
  Keyed the analytics forms by their applied query so controls remount with applied filters.
- Both workflows and both deployments passed on the feature commit; Reset follow-up
  deployment acceptance is recorded in the final delivery notes.

## Missing-data assessment — November 3, 2026

- Added protected `/api/v1/dataset/missingness` and Missing data website page.
- All 13 supported metrics: non-null/zero counts, calendar gaps, absent fields and explicit
  nulls, first/last observed values and separate leading/internal/trailing unavailability.
- Consecutive calendar missing/observed runs, descriptive gap-length distribution,
  complete/full/sliced months and longest complete-month streaks for target assessment.
- Selected-metric gap/month tables, inclusive date filters, independent pagination,
  source-investigation links, input fingerprints and visible assessment limitations.
- Causes are unassessed: parser support and temporal patterns are not proof of structural
  absence, parser failure, official-report unavailability, recoverability or missingness mechanism.
- No imputation, corrections, target selection, prepared model dataset or forecasts.
- Local checks: 133 backend tests passed in the full environment; 13 frontend tests,
  Ruff, compilation, TypeScript and production build passed. One PostgreSQL integration
  remains skipped. The same 133 tests also pass in the pinned foundation environment.
  Deployed browser acceptance is a separate check.
- Policy, definitions, evidence limits, Windows commands and manual tests: MISSING_DATA.md.



## Research preparation — November 3, 2026

- Added protected read-only preparation API and authenticated Research preparation page.
- Explicit one-metric study window and chronological training/validation/test cutoffs;
  every calendar date retained with original values, evidence states and source/version lineage.
- Default observed-only baseline and optional experimental previous-week training-only
  candidate: 1–3-day internal runs, original t-7 donor, no recursive fill, no boundary fill,
  no review-held value substitution, known/timely donor availability required.
- Validation/test targets never filled. Original numerical flags retained and conservative
  research holds applied separately; no database/source/review decisions changed.
- Five-file downloadable research bundle with original snapshot, numeric daily values,
  daily audit, strictly observed additive monthly totals and checksummed manifest.
- Stable input/config snapshot ID and stale-preview download protection. Bundles are not
  persisted server-side; download to retain. Not a point-in-time backtest/model registry.
- Local verification: 149 backend tests passed, 1 opt-in PostgreSQL integration skipped;
  15 frontend tests passed, Ruff, TypeScript and production build passed.
- Source verification/recovery, treatment accuracy comparison, accepted study/split design,
  rolling-origin modelling and model results remain pending. Weekly candidates are not
  approved thesis imputations. See RESEARCH_PREPARATION.md for protocol and manual tests.
- Previous missingness live acceptance confirmed: 2,383 canonical dates /2,571 calendar
  days, 188 gaps; cost 626 observed days with 22 internal missing days. Full leap-month,
  partial-month and Reset behavior verified in production.

## Live preparation acceptance — 3 November 2026

Tested the deployed preparation page against Neon after secure sign-in.

- Energy generated, 2024-01-01 through 2024-12-31; training cutoff 2024-06-30,
  validation cutoff 2024-09-30.
- Split calendar/observed/missing counts: train 182/171/11, validation 92/78/14,
  test 92/42/50. Zero numerical review holds in this selected window.
- Observed-only baseline: 366 unique, continuous calendar rows, 291 original canonical
  records, zero estimates and no prepared-training values on validation/test rows.
- Downloaded all five members. All four manifest member hashes matched; reconstructing
  the snapshot ID from exported original evidence/config matched the live preview.
- Numeric CSV values matched the audit CSV row-by-row and original measurement snapshot;
  available monthly totals reconciled exactly. Only February and August 2024 met the
  complete, observed/unheld monthly-total gate in this selected window.
- Baseline ID: 0e959965c6eac65797d38751ec4b2ea70c3072975a00ff14e5a1580ead08d30e.
  Reset and re-preview reproduced the same ID.
- Experimental one-day policy ID:
  24db81632763f1bcb2fa4fc8ad57de3dc737dac153319868af287610d90be49a.
  Zero estimates: seven missing training days had unknown donor availability,
  one lacked a usable original weekly donor, two exceeded the one-day run limit,
  and one was a boundary gap. All 64 missing held-out days stayed unfilled.
  Experimental bundle member checksums matched.
- Equal training/validation cutoffs displayed a clear validation message and no preview.
  Reset cleared all four dates and restored the baseline with no applied preparation.
- Desktop visual layout checked. This does not constitute independent PDF verification,
  source recovery, historical point-in-time validation or a mobile acceptance test.
- The 75 unavailable 2024 calendar dates are a canonical-data finding, NOT proof that
  official PDFs are absent. Source/quarantine investigation remains the next priority.

## Canonical-gap recovery investigation — November 3, 2026

- Added selected gap-date windows to Source audit, preserving both pagers and page-size forms.
- Added protected complete recovery-worklist JSON export: all dates across pages, explicit
  bounded window, counts, evidence-detail truncation and versioned content identity.
- Added local read-only ingestion.reconcile_gaps for explicit historical batch and journal:
  exact extraction-date candidates vs same/next-day archive hints, all journal revisions,
  path/size/SHA checks, parser issue codes, local evidence fingerprints and new output report.
- No PDF dates independently verified, no originals/journal/Neon changed, and no recoveries
  or approved imputations claimed. Full historical archive remains on the user's Windows PC.
- Local checks: 162 backend tests passed, 1 opt-in PostgreSQL integration skipped; 17 frontend
  tests, Ruff, TypeScript and production build passed. Live worklist acceptance follows deployment.
- Windows command, evidence semantics and review workflow: GAP_RECOVERY.md.
