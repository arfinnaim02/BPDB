# Verified observed-only 2024 research baseline

This hosted export includes the four reviewed 2024 repairs without modifying Neon
or replacing the collection checkpoint. It uses the existing preparation builder
and its snapshot identity, review holds, calendar handling and five-file bundle.

## Research configuration

| Setting | Value |
| --- | --- |
| Metric | Energy generated, million_kWh |
| Study window | 2024-01-01 through 2024-12-31, inclusive |
| Training | January through June |
| Validation | July through September |
| Test | October through December |
| Policy | observed_only; zero estimated values |

These are the previously used illustrative chronological split boundaries. They
are not a finding that this year or these boundaries are optimal for modelling.
The repaired dates are 1 January, 4 January, 20 April and 25 May 2024. All twenty
supported measurements and their exact source URL/SHA/page lineage must be present.

## Online execution and preservation

GitHub Actions **BPDB verified research snapshot** runs when its workflow file is
pushed to main, or via Run workflow. It uses existing Drive and database secrets.
The fixed study configuration prevents accidental treatment or split changes.
Database access is through the existing repeatable-read/read-only session.

The worker freezes the data once, closes the database session and builds the bundle.
It reopens that bundle to verify every internal file hash and byte length, snapshot
identity, all 366 calendar dates, clean CSV/audit agreement, split counters, held-out
training blanks and exact reviewed repair lineage. Missing dates remain blank.

The same existing bundle files are retained: original_snapshot.json, daily_values.csv,
daily_audit.csv, monthly_observed.csv and manifest.json. Verification and Drive storage
receipt are separate outer artifacts. The bundle, report and receipt are saved as
immutable content-addressed Drive blobs with remote checksum verification. No
credentials or full PDF archive are included. GitHub retains the diagnostic package
for 30 days; durable storage is Drive.

This adds durable hosted archiving to the CLI workflow. The existing website export
remains request-based and does not persist its own copy. To reproduce the snapshot
on the website, use the table's configuration and compare the snapshot ID. A later
canonical revision may yield a different ID; the archived bundle remains frozen.
ZIP bytes can differ because of creation metadata while content snapshot identity
remains the same. Both identities are recorded for their distinct purposes.

## Research interpretation

Observed counts include source-derived values with review holds. Consult the held
and observed-target-candidate counts before analysis or scoring. Calendar gaps do
not prove that official reports never existed. No artificial masking experiment,
imputation accuracy result, forecasting model or best-model claim is produced here.
Only fully observed and unheld calendar months receive additive monthly totals.

Next: inspect the verified split/coverage report, then compare observed trends and
coverage together. Missing-data treatment experiments must use training data only
and realistic masks; validation/test targets remain observed and untouched.

## Hosted acceptance — 4 November 2026

[Run 41829042019](https://github.com/arfinnaim02/BPDB/actions/runs/41829042019)
completed successfully at implementation commit
`158d7f12d9e5acd3ff1de05b6da006178147eb03`.

Content snapshot ID:
`4f35dcb7da194025f79f2f7fb8ed52066e599c96f72e7cd0fc62c691fb4883a1`.

Archived bundle SHA-256:
`86904e6812876ac12184434fe66acb388f2f6b626f2d2221600d788f4ffee4da`.

| Split | Calendar days | Observed values | Missing values | Review holds |
| --- | ---: | ---: | ---: | ---: |
| Training | 182 | 175 | 7 | 0 |
| Validation | 92 | 78 | 14 | 0 |
| Test | 92 | 42 | 50 | 0 |
| Total | 366 | 295 | 71 | 0 |

The four repaired dates and all twenty reviewed measurements passed exact-value,
dimension and PDF-lineage verification. Estimated values=0; Neon writes=0;
checkpoint_replaced=false. All five inner files and clean CSV/audit consistency
passed. The archive, verification report and storage receipt were remotely
checksum-verified in Drive, and the diagnostic artifact was published in GitHub.

The hosted export safety gate passed 23 tests. The local full backend suite passed
217 tests with one opt-in Postgres integration test skipped. Backend and Foundation
workflows and both Vercel deployment checks passed for the implementation commit.

This snapshot has 50 missing test-period days out of 92; results on its 42 observed
test targets cannot be described as full-quarter performance. Zero implemented
review holds does not certify every source value as error-free. Keep these limits
visible in subsequent comparisons and choose modelling periods only after a
documented coverage and definition-comparability assessment.
