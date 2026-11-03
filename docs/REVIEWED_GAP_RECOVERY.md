# Reviewed January 2024 recovery

This workflow accepts exactly two previously inspected original PDF revisions:

| PDF | Operational date | Reporting date | Measurements |
| --- | --- | --- | --- |
| 7390page1.pdf | 2024-01-01 | 2024-01-02 | 5 |
| 7396page1.pdf | 2024-01-04 | 2024-01-05 | 5 |

The immutable URL, SHA-256, dates and five expected values are pinned in
`backend/ingestion/reviewed_recovery.py`. Source review and PDF geometry
evidence are documented in `SOURCE_GROUNDED_PARSER_REPAIR.md`.

## Hosted execution

GitHub Actions **BPDB reviewed gap recovery** runs automatically when its own
workflow file changes on main, or through Run workflow. It shares the daily
worker concurrency group and uses the existing private Drive and Neon secrets.
No local files, full archive download or new secrets are required.

1. Run parser and recovery tests before credentials are prepared.
2. Download the two already archived PDF blobs and verify their exact SHA-256.
3. Reparse, validate, and compare every expected date, metric, unit and value.
4. Preview source registration needs and canonical/conflict eligibility.
5. Stage both dates in one transaction without changing canonical pointers.
6. Read back all ten measurements in a separate process and transaction.
7. Verify again under date locks, then promote both gaps in one transaction.
8. Verify again; an identical repeat inserts no measurements and promotes none.

Competing partial/validated/conflict versions stop the job. Existing unrelated
canonicals are never replaced. Old quarantined versions and source records are
preserved. Unknown original publication/availability timestamps remain unknown.

Every action saves a timestamped JSON report as a verified immutable Drive blob;
GitHub retains diagnostic JSON artifacts for 30 days. Stage and promotion also
record the reviewed extraction and review fingerprint in Neon ingestion runs.
The shared collection checkpoint is never replaced by this job.

If a reviewed PDF is not registered yet, staging creates its source record in
the same transaction as the measurements. Its storage key identifies the exact
archived Drive blob. Retrieved-at is the actual archived-byte download time;
publication time and archive-date hint remain unknown. Existing source records
are reused by URL plus checksum. A failed second date rolls back both dates.

## Acceptance

Before deployment, both original PDFs pass the pinned validation gate locally.
Tests cover checksum/date/value/unit/parser/issue mismatches, all stored numeric
dimensions, missing links, competing canonical records, real importer staging
and repeated promotion. SQLite tests do not exercise PostgreSQL advisory locks;
the hosted job provides the real Neon acceptance check.

Successful first execution should insert 10 measurements and promote 2 dates.
Successful repeats should insert 0 and promote 0, with already_canonical=2.
If no other recovery occurs concurrently, 2024 canonical gaps fall from 75 to 73.
These two repairs do not establish complete historical coverage or resolve the
other gaps or historical numerical-review flags. Analysis snapshots should be
regenerated after confirming hosted acceptance.
