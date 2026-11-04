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
