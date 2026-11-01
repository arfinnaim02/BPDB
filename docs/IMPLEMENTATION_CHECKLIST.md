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
