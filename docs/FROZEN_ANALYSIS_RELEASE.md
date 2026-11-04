# Frozen descriptive analysis release

Bundled release, 4 November 2026. New authenticated page: /analytics/research.
Existing live history/comparisons remain available separately.

## Included together

1. Daily energy chart and trailing seven-calendar-day mean, with explicit gaps.
2. Monthly mean profile with a separate coverage-percentage axis.
3. Monthly and quarterly mean, median, minimum, maximum and sample SD tables.
4. Weekday mean profile and distribution/coverage table.
5. Chronological split audit and exact monthly daily-value/PDF evidence table.
6. Four clean CSV exports plus complete analysis JSON with identity and lineage.

## Fixed input and reproducibility

The verified hosted research bundle from run 41829042019 is the input, not a
second live-data query or a competing master dataset. Snapshot ID:
4f35dcb7da194025f79f2f7fb8ed52066e599c96f72e7cd0fc62c691fb4883a1.
Bundle SHA-256: 86904e6812876ac12184434fe66acb388f2f6b626f2d2221600d788f4ffee4da.

The generator reuses the bundle/hash/calendar/split/repair verifier and refuses
a different snapshot ID. It produces a compact compressed JSON asset packaged
with the backend. The API verifies its snapshot and full analysis hash before
serving it; missing/corrupt data produces 503 rather than sample data. The
original ZIP remains in private Drive and the hosted diagnostic artifact. The
derived asset introduces no database writes or new cloud credentials.

To regenerate from the retained bundle with PYTHONPATH=backend:

```text
python -m ingestion.analyze_frozen PATH_TO_VERIFIED_BUNDLE.zip backend/app/data/frozen_2024_analysis.json.gz
```

Analysis ID: 1ef8685343f9532c41896a340551b4a035f1e0ede568929d57c3907ba7f9c18e.
Rules: frozen_energy_descriptive_v1. Gzip uses deterministic metadata.

## Statistical rules

- Source values stay exact; derived Decimal statistics round to six decimal places.
- Means/medians/SD/min/max use original observations with no implemented review hold.
  Zero remains zero. Empty groups have blank statistics; sample SD requires n >= 2.
- A seven-day mean needs every one of the current and six prior calendar days to
  be observed and unheld. Missing dates and holds break the series. No future days,
  interpolation, recursive fill or coverage scaling are used.
- Monthly/quarterly energy totals require every calendar day eligible. A partial
  sum is never presented as a complete total. MoM energy-total changes require
  two complete adjacent months and nonzero previous total. Different month lengths
  remain visible. No complete annual total is inferred from incomplete coverage.
- Weekday groups compare observed date mixtures; no causal weekday effect is claimed.
  One year shows a monthly pattern, not established recurring annual seasonality.
- Test dates remain unaltered and are visibly audited. Descriptive display is not a
  model-selection experiment or untouched prospective evaluation. Model specifications
  must be chosen under a separate training/validation protocol.

The input contains 295 observed values and 71 missing calendar days, with zero current
implemented holds. Only February, May and August have complete monthly totals.
Test coverage is 42 of 92 days. No forecasts, model accuracy or imputation performance
claims are introduced.

## Access and validation

Backend endpoint: /api/v1/analytics/frozen-2024; existing administrative key protection
applies. Optional downloads are allowlisted to daily/monthly/quarterly/weekday/report.
Frontend uses the existing server-side signed session and backend key; no credentials
are exposed to the browser. CSV headings contain units and cells contain values/blanks;
lineage and interpretation stay in JSON. Invalid download kinds return 422.

Local verification: 223 backend tests passed, one opt-in database integration skipped;
18 frontend tests passed; Ruff, TypeScript and production build passed. Tests cover
zero/empty/sample-SD cases, incomplete totals, gap-safe trailing windows, corrupt assets,
auth, export bounds and actual packaged snapshot counts. Authenticated local HTTP checks
returned 200 for the page, a May daily-table selection, and all five export kinds.
The cloud browser could not connect to the local preview, so responsive visual inspection
was not completed. The page uses existing responsive shell/table/chart conventions and
adds scoped responsive download-menu styling. Deployment acceptance is recorded separately.

## Production checks

1. Sign in and open Frozen research analysis. Confirm 295 observations /71 gaps.
2. Zoom the daily chart; missing intervals must not connect or gain seven-day means.
3. Monthly table: February, May and August have totals; incomplete months stay blank.
4. Select May in the daily table; 25 May shows 337.88 (stored 337.880000) and its original PDF link.
5. Download CSVs: 366 daily, 12 monthly, 4 quarterly and 7 weekday rows, plus headings.
6. Open JSON and compare snapshot/analysis IDs above. Live master updates must not
   silently modify this fixed release.

## Deployment acceptance — 4 November 2026

Implementation commit `48ea0cd2caef40db1e1536cb05e7eb57ca83d6b8` passed
Backend checks, Foundation checks (including frontend tests/typecheck/build), and
both Vercel deployment status checks. The compressed verified data asset is included
explicitly in the backend function package. The final presentation refinement uses
three-letter weekday axis labels on the chart; tooltips/tables retain full names.

This confirms CI and deployment completion, plus the local authenticated HTTP
acceptance described above. Signed-in production visual/mobile interaction remains
unverified; no such browser acceptance is claimed.
