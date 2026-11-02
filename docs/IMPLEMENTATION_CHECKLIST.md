# Implementation checklist — November 1, 2026

## Acquisition and canonical dataset

- [x] Repository, database schema, migrations and health endpoints.
- [x] Historical PDF collection and incremental archive scanning.
- [x] Supported Page 1 national extraction, validation and quarantine.
- [x] Source registration, staging and database consistency verification.
- [x] Canonical promotion and repeat-ingestion checks on the initial imported batch.
- [x] Authoritative database-derived CSV export.
- [ ] Complete independent source-sample audit and per-metric historical coverage assessment.
- [ ] Investigate calendar gaps, failed extractions and ambiguous/conflicting sources.
- [ ] Extract supported regional, fuel-wise and recorded load-shedding fields.

## Daily operation

- [x] Hosted worker, private credentials, serialized workflow writes.
- [x] Recent-file/checkpoint persistence and checksum-verified restore.
- [x] Successful manual and scheduled hosted execution.
- [ ] Observe sustained scheduled operation and add failure notifications.
- [ ] Detect replacements at already-known URLs.
- [ ] Complete historical cloud backup and full disaster-recovery test.
- [ ] Persist/link Drive outcome to the corresponding database run.

## Data-management platform

- [x] Protected summary and daily-worker history endpoints.
- [x] Protected paginated current master records, date filters and provenance.
- [x] Automated canonical filtering, authentication, pagination and consistency tests.
- [ ] Authenticated live acceptance of the newly committed API against Neon.
- [x] Dashboard filtered CSV download with export timestamp, version/source lineage and HTTP checksum.
- [x] Real-data Overview, Collection, Dataset and Data Quality frontend pages implemented.
- [x] Signed workspace sessions and server-only backend credentials.
- [ ] Live browser acceptance of website, source evidence and CSV against Neon.
- [ ] API/frontend hosting and deployed end-to-end acceptance.

## Research

- [ ] Data dictionary, variable coverage, target feasibility and availability-time policy.
- [ ] Independently verified historical aggregations and analytics.
- [ ] Chronological baselines, walk-forward evaluation and reproducible model artifacts.
- [ ] Forecast dashboards, uncertainty and evidence-backed decision support.
- [ ] Frozen report snapshots and analytical PDF generator.
- [ ] Verified literature, thesis draft and defense materials using actual outputs.



## CSV presentation

- [x] Values-only daily export with one row per date and descriptive unit headings.
- [x] Separate source-evidence export retaining detailed provenance.
- [x] Precision, null/zero, date-filter and dimension tests.
- [ ] User acceptance of downloaded daily/evidence CSV against live Neon records.


## Hosting
- [x] Prepare backend/frontend Vercel configuration and deployment guide.
- [x] Add an explicit hosted CSV size guard with a regression test.
- [ ] Import backend project and verify live/readiness plus authenticated data.
- [ ] Import frontend project, configure private environment and verify live workspace.
- [ ] Verify CSV, source links and scheduled updates with local terminals closed.


## Full-history data quality
- [x] All-current-canonical metric availability, including zeros and preserving dimensions.
- [x] Calendar coverage per year, including partial boundary years and missing entire years.
- [x] Metric year selector and earliest/latest non-null dates.
- [x] Inclusive calendar-gap ranges, pagination and explicit unassessed source status.
- [x] Aggregation, exclusions, date edge cases, auth and pagination tests.
- [ ] Verify the deployed quality page and API against live Neon.
- [ ] Investigate source causes and independently validate selected original PDF measurements.


## Registered source audit
- [x] Gap-date registered report/version/source/issue evidence.
- [x] Separate archive hints and explicit unknown official-report availability.
- [x] Undated held-source queue and bounded/paginated evidence.
- [x] Targeted original-PDF comparison plan with preserved source provenance.
- [x] Read-only/auth/privacy/pagination/association and sample-integrity tests.
- [ ] Verify deployed audit page against live Neon metadata.
- [ ] Inspect original PDFs and record independent comparison findings.
- [ ] Reconcile historical local quarantines/failures not registered in Neon.
- [ ] Repair eligible gaps only through reviewed versioned ingestion.


## Generation and demand descriptive analytics
- [x] Authenticated observed-series API, inclusive date filtering and canonical/version scope.
- [x] Daily/monthly/yearly views; correct MW averages and observed energy sums.
- [x] Null/zero, calendar completeness and layout-dependent availability labels.
- [x] Decimal descriptive statistics and source-record drill-down.
- [x] Zoomable ECharts line chart, exact period table and frontend filters.
- [x] Aggregation, date, precision, integrity, authentication and filter tests.
- [x] Deployed browser/Neon acceptance of new chart and API for generation/energy views.
- [ ] Independent PDF checks and interpretation before inferential or forecasting claims.

## Measurement review and research gates — November 2, 2026
- [x] Authenticated read-only national energy/generation review API and website queue.
- [x] Explicit consistency rules and separately labelled heuristic threshold.
- [x] Source evidence, rule counts, filters/pagination and request fingerprint.
- [x] Legacy split/malformed energy token protection with regression tests.
- [x] Representative local legacy/modern PDF extraction checks.
- [x] Documented research readiness, source correction and chronological evaluation protocol.
- [x] Live acceptance of the new measurement review page, filters and evidence against Neon.
- [ ] Confirm the original 4 January 2020 PDF and other flagged source values.
- [ ] Durable reviewer decisions and independently assessed extraction accuracy.
- [ ] Reviewed versioned historical repairs; rerun consistency checks and exports.
- [ ] Freeze a manifest-backed research dataset and assess complete-month target feasibility.
- [ ] Execute and report chronological baseline/model experiments using actual data.

## Historical comparison dashboard — November 2, 2026
- [x] Protected comparison API, paired generation/demand means and signed differences.
- [x] Matched daily observations, explicit calendar coverage and missing-value gaps.
- [x] Seasonal year profiles, year-by-month heatmap and weighted annual summaries.
- [x] Complete-month MoM/YoY comparison gates with unavailable/zero-baseline reasons.
- [x] Date/year filters, daily/monthly/yearly paired views and preserved pagination.
- [x] Source links, unresolved-screen warnings and request fingerprints.
- [x] Automated comparison/filter/chart-input tests and documented manual acceptance list.
- [ ] Deployed browser acceptance of the new comparisons dashboard against Neon.
- [ ] Independent source verification and final analysis interpretation before modelling.


