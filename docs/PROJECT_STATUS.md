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


## Release 1 — executed forecasting study, November 5, 2026

- Completed the 2020–2023 training /2024 validation /reserved 2025 test experiment for national daily energy generated. Frozen snapshot, two benchmarks, Ridge, training-only missing-input comparisons and model/prediction downloads are delivered.
- Successful hosted run: https://github.com/arfinnaim02/BPDB/actions/runs/41983140391. Results are archived privately in Drive and served from a verified frozen asset through the protected API.
- Added authenticated Forecast experiments page: actual/predicted chart, common-date and monthly errors, training selection, masking coverage, exact monthly predictions and five exports.
- On 220 identical validation dates, Ridge MAE/RMSE 18.1441/27.3086 million kWh; lag-2 benchmark 19.2274/29.9165; lag-7 benchmark 29.1578/41.5755. No statistical-significance or final-model claim.
- Selected training configuration: previous-week original input donor, Ridge alpha 0.1; 1,313 final fit rows. Missing evaluation targets remain unfilled. No Neon writes.
- Strict verified historical publication-time coverage is 0/366 validation days. This is an explicitly assumed retrospective reporting-delay scenario using current canonical revisions, not verified live accuracy.
- Full backend research environment: 233 passed, 1 opt-in PostgreSQL test skipped. Frontend: 20 passed; Ruff, TypeScript and production build passed. Numerical output hashes, saved inference and common-date scores independently checked.
- Final 2025 test remains unevaluated. Next: predefined statistical/tree alternatives, training-only selection, validation comparison, then freeze and authorize final-test evaluation.
- Protocol and actual results/acceptance checklist: [RELEASE1_PROTOCOL.md](RELEASE1_PROTOCOL.md), [RELEASE1_TEST_REPORT.md](RELEASE1_TEST_REPORT.md).


## Release 2 — predefined model comparison, November 5, 2026

- Added autoregressive OLS, Random Forest and Gradient Boosting, with five predefined new configurations and exact Release 1 frozen input. No database writes or new snapshot selection.
- Hosted run succeeded: https://github.com/arfinnaim02/BPDB/actions/runs/41991685905. Safe JSON models, predictions and reports are archived in private Drive.
- Same 755 training-fold dates for all family finalists; OLS selected provisionally before validation. Final new models use 1,313 rows through last usable label 2023-12-25.
- Six-method comparison on identical 220 validation dates: MAE lag2 19.2274, lag7 29.1578, Ridge 18.1441, OLS 18.1426, forest 22.0533, boosting 22.9775 million kWh. OLS/Ridge are practically tied; tree configurations do not improve this comparison. No significance or final-test claim.
- Added protected Release 2 API, authenticated Model comparison page, chart, monthly errors, selection/fold evidence, model checks and five downloads. Release 1 remains available.
- Local checks: 245 backend tests passed, 1 opt-in PostgreSQL integration skipped; 23 frontend tests, Ruff, TypeScript and production build passed. Independent manifest and score recomputation passed.
- Historical availability remains unknown (strict feature coverage 0/366). Retrospective assumption only; 2025 remains reserved.
- Next: freeze final evaluation design, run the reserved-year evaluation once, then integrate the evaluated research model and write thesis results.
- See RELEASE2_PROTOCOL.md and RELEASE2_TEST_REPORT.md for actual evidence, limits and researcher acceptance checks.


## Release 3 — locked 2025 final evaluation, November 5, 2026

- Primary OLS and all fixed references refitted on eligible pre-2025 labels with no model switching or test parameter updates. Nominal cutoff 2024-12-30; 1,557 actual rows; last usable label 2024-10-18.
- Hosted final evaluation succeeded: https://github.com/arfinnaim02/BPDB/actions/runs/42010041257. A verified private Drive receipt binds protocol/code key to retained outputs; repeat hosted runs restore the result.
- Test sample: 365 calendar days, 330 eligible observed targets, 287 all-method common scored dates; OLS forecasts 311 dates and scores 303 on its own available targets. Missing targets remain unfilled.
- Common MAE/RMSE million kWh: lag2 17.9007/23.3982; lag7 21.7705/28.4908; Ridge 15.5000/19.7754; primary OLS 15.5000/19.7758; forest 19.2124/24.0754; boosting 20.2079/24.9544. OLS MAE is 13.41% below lag2; OLS/Ridge practically tied. No post-test switching.
- Predeclared paired circular-block sensitivity (7/14/28 days, 2,000 resamples) reports descriptive ranges, not prediction intervals or significance claims.
- Added protected Final evaluation API/page, test charts, monthly scores, validation/test comparison, model card and seven individual downloads. Historical Release 1/2 pages link to the later evaluated-year result.
- Local checks: 262 backend tests passed, 1 opt-in PostgreSQL integration skipped; 26 frontend tests, Ruff, TypeScript and production build passed. Artifact/manifest hashes and six final scores independently verified. A test-only lightweight CI dependency import was isolated; worker algorithm/results unchanged.
- Historical availability remains unknown: strict feature coverage 0/365. Results are a disclosed retrospective scenario, not verified live accuracy. 2025 is now evaluated and cannot be reused as an untouched holdout.
- Next: separately identified research forecast service and prospective availability tracking, then thesis methods/results/figures grounded in retained evidence.
- See RELEASE3_PROTOCOL.md and RELEASE3_TEST_REPORT.md for final evidence, limitations and acceptance checks.


## Release 4 — prospective research forecasts, November 5, 2026

- Added separate Neon forecast/outcome tables via 0003; hosted upgrade and Alembic check passed. Master observations/canonical pointers remain separate; original source-table counts unchanged in acceptance.
- Uses exact saved Release 3 OLS model, no retraining. Actual issue/capture times, bounded original-donor inputs, source/version IDs, checksums, features and linear arithmetic retained. Identical reruns reuse the original issue/time; changed snapshots preserve distinct attempts.
- First real issue: target 2026-11-06, issued 2026-11-05 18:41 Bangladesh, prediction 320.957156601 million kWh. Latest used original 2026-11-03; one input slot used the prescribed previous-week original. Nine official publication times unknown; platform capture retained before actual issue.
- Daily workflow now issues after successful collection and verified Drive checkpoint, with explicit withheld attempts and infrastructure error reporting. Later eligible completed-day actual revisions are appended separately over a 90-day reconciliation window.
- Added authenticated Research forecasts dashboard and read-only APIs, history CSV and complete issue JSON. Prospective summary uses earliest successful issue per target and latest retained actual; initially zero scored dates, no invented accuracy.
- Verification: 279 backend tests passed, 1 opt-in PostgreSQL test skipped; 29 frontend tests, Ruff, TypeScript and production build passed. Real hosted migration, idempotency, source-date/capture and saved inference checks passed.
- Historical model age, retrospective evaluation assumptions and unknown official times remain visible. No operational accuracy or forecast interval is claimed.
- Next: thesis-ready figures, automated research report and methods/results drafting using retained evidence; collect prospective outcomes before current-accuracy claims.
- See RELEASE4_PROTOCOL.md and RELEASE4_TEST_REPORT.md.

## Release 5 — research report and figure exports, November 7, 2026

- Added authenticated Reports page, seven-page PDF, four vector SVG figures, methods/results Markdown, twelve-row model CSV and snapshot-bound JSON. Frozen historical results and changing prospective evidence remain separate.
- First hosted Neon capture: 2,390 canonical dates through November 4; prospective zero scored dates. All eight export hashes and PDF pagination/layout verified; 292 backend tests passed (1 skipped), 31 frontend tests, Ruff, TypeScript, production build and authenticated HTTP download checks passed.
- Report workflow runs manually and after successful trusted-main daily collection. Drive archival is **blocked** by expired/revoked OAuth authorization (`invalid_grant`); generated files remain in the GitHub artifact. No successful Drive archive is claimed. Renew the token before expecting unattended storage-dependent collection to continue.
- See RELEASE5_PROTOCOL.md and RELEASE5_TEST_REPORT.md for evidence, recovery instructions and dashboard checks. Next: full thesis narrative/literature review and continued prospective outcome collection; no reuse of evaluated 2025 as untouched holdout.

### Release 5 detailed-results expansion

- Expanded PDF from seven to 18 pages and added complete detailed Markdown/JSON appendices; dashboard now exposes error-tail/direction and monthly coverage tables. All six models retain their original frozen scores.
- Added deterministic descriptive quantiles and largest-error diagnostics, not new models or inference. OLS median absolute error 12.7500, 90th percentile 33.2086, 95th 37.9161, maximum 86.2362 million kWh on 287 common dates; 178 underpredictions, 109 overpredictions; 161 dates with lower absolute error than lag 2.
- Acceptance: 293 backend passed, one skipped; 31 frontend passed; Ruff, typecheck, build and authenticated report/all-export checks passed. 18 PDF pages rendered and visually checked. Drive authorization remains the previously disclosed external blocker.

## Analysis-first frontend rebuild — November 7, 2026

- Rebuilt shared frontend theme/navigation and research Overview. Added Explore data studio (six chart types, filters, CSV/SVG downloads, exact daily table) and evidence-based descriptive Planning insights.
- Added matched-date error/bias charts to Final evaluation. Original experiment assets, authentication, canonical database, automation and report outputs are unchanged.
- 38 frontend tests, TypeScript, production build and 13 isolated authenticated HTTP acceptance groups passed. Six studio configurations rendered as SVG at desktop/mobile widths. Full browser visual review remains unverified because managed preview passed unsupported Next.js startup arguments.
- Current Drive authorization recovery is verified by successful daily collection 42396876427 and research report/archive 42397161685; earlier blocked notes above are historical.
- See ANALYSIS_WORKSPACE_REDESIGN.md for formulas, limitations and user acceptance. Original cost/demand/zonal objectives and complete thesis remain separate outstanding research work.

## Multivariable descriptive and exploratory analysis — November 8, 2026

- Replaced the Explore entry with a one-to-eight-variable workspace covering thirteen supported national measurements, including modern temperature, gas and costs. Original single-variable studio remains at /explore/single.
- Added full descriptive statistics, adjusted moments, paired Pearson/Spearman/first-difference relationships, twelve chart configurations, source-bound aligned CSV/JSON exports and explicit coverage/units/sample sizes.
- Backend and data source are read-only. No model refits, canonical edits, causal claims or imputation. Same-window scaling is exploratory only; undefined correlations and statistics remain unavailable.
- Local checks: 301 backend passed, one skipped; 43 frontend passed; 36 independent NumPy/SciPy formula checks; twelve chart SVG configurations at mobile/desktop sizes; TypeScript/build and authenticated HTTP acceptance passed. Hosted real-Neon acceptance and deployment are recorded separately.
- See MULTIVARIATE_EDA.md for exact formulas, safeguards, interpretation and acceptance.
