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
- [x] Deployed browser acceptance of counts, paired values, legacy nulls and source drill-down.
- [ ] Independent source verification and final analysis interpretation before modelling.

## Missing-data assessment — November 3, 2026
- [x] Read-only availability assessment for all 13 supported national metrics.
- [x] Separate canonical-gap, absent-field, explicit-null and observed-zero states.
- [x] Leading/internal/trailing unavailability and calendar-based run/streak statistics.
- [x] Complete, incomplete and sliced months with consecutive complete-month counts.
- [x] Filtered/paginated frontend evidence views, source links and input fingerprints.
- [x] Integrity/auth/no-store, state partition, leap/calendar, completeness and filter tests.
- [x] Documented evidence-first treatment policy with training-only preparation rules.
- [x] Confirm production results and browser acceptance against live Neon.
- [ ] Verify missing causes and recover source-supported values through reviewed ingestion.
- [x] Implement a separate lineage-preserving research candidate export.
- [ ] Evaluate and approve treatments after source investigation.



## Research preparation — November 3, 2026
- [x] Separate read-only research candidate with original values and complete calendar.
- [x] Explicit chronological train/validation/test cutoffs; held-out targets never filled.
- [x] Default observed-only policy plus optional auditable, bounded previous-week candidate.
- [x] Donor original-value/provenance/timely-availability gates; no recursive or boundary fill.
- [x] Conservative numerical-review holds without modifying master values or review decisions.
- [x] Downloadable original snapshot, values/audit CSVs, observed monthly totals and manifest.
- [x] Input/config identity, member checksums, stale-preview protection and protected downloads.
- [x] Automated split, donor, zero, hold, leakage, month, identity, bundle and API/filter tests.
- [x] Production acceptance of new preparation preview and downloadable bundle.
- [x] Both live bundle checksums, reconstructed snapshot ID, original-value reconciliation,
  held-out blanks, monthly totals, experimental donor refusals, invalid splits and Reset.
- [ ] Source-supported historical recovery and durable independently reviewed decisions.
- [ ] Compare missing-data treatments on realistic chronological training folds.
- [ ] Approve target definitions/sample feasibility, freeze accepted experiment and train models.

## Canonical-gap recovery investigation — November 3, 2026
- [x] Filter missing canonical dates without losing edges or gap-only windows.
- [x] Complete bounded worklist export independent of visible pagination.
- [x] Read-only local journal/batch reconciliation with explicit candidate evidence states.
- [x] All saved revision matching, path bounds and size/SHA verification.
- [x] Worklist/local metadata fingerprints and non-overwriting investigation reports.
- [x] Backend integrity/auth/calendar/reconciliation tests and frontend filter tests.
- [x] Confirm deployed 2024 worklist includes all 75 current gap dates and preserves filters.
- [x] Verify all-date export from page two, content identity, preparation-gap agreement and Reset.
- [ ] Run local reconciliation against actual historical PDFs and inspect its output.
- [ ] Verify original PDFs, correct supported parser cases and review conflicts.
- [ ] Stage/verify/promote recovered source-supported values and create a new research snapshot.

## Hosted gap investigation — November 3, 2026
- [x] Online bounded GitHub job with existing secrets and quoted/validated manual inputs.
- [x] Read-only current worklist and checksum-verified checkpoint journal candidate selection.
- [x] Verified Drive-PDF reuse and bounded official retrieval with distinct immutable PDF blobs.
- [x] Parser/validation/date-match findings and bounded first-page text diagnostics.
- [x] Verified report/worklist/plan/receipt preservation without daily checkpoint replacement.
- [x] Diagnostic-only GitHub artifacts and credential cleanup; no canonical imports/promotions.
- [x] Unit tests for URL, hint, cached-byte, failure, date/checksum and bounded-run behavior.
- [x] Complete first real hosted acceptance and inspect actual candidate findings.
- [x] Verify real PDF/text/report preservation, artifact checksum and zero database promotions.
- [ ] Independently verify PDFs, resolve supported parser/source cases, stage and promote repairs.
- [ ] Complete backup of the historical home-PC archive if original-byte continuity is required.

## Source-grounded parser geometry repair — November 3, 2026
- [x] Retrieve preserved originals and inspect enlarged source-summary renders.
- [x] Identify default-tolerance row merging and add deterministic small-font extraction.
- [x] Preserve strict numbers, date/metric ambiguity guards and unchanged normal-font extraction.
- [x] Exact-value/date/unit fixtures for repaired sources and normal legacy/modern references.
- [x] Reject mislabeled station-table source with an explicit unsupported-kind code.
- [x] Record extraction geometry, parser SHA/runtime and bounded hosted PDF/text evidence.
- [x] Local suite passes: 187 backend tests, one optional PostgreSQL integration skipped.
- [x] Complete hosted repaired-parser acceptance and inspect resulting candidates.
- [x] Verify both repaired days, explicit non-summary rejection, runtime identity and artifact hash.
- [ ] Stage and verify reviewed source-supported repairs before previewing canonical promotion.
