# Missing-Data Treatment Study — predefined protocol v1

Decision: study missing energy feature inputs before any retraining. This protocol and executable code are committed before the first real-data execution. Artificial reconstruction is not a downstream forecasting experiment.

## Frozen identity and isolation

- Input ZIP SHA-256: `bbcf319b97029d15a8180849b3f7ca218ef1e3ef7debf4ed01d32c511516c81a`.
- Snapshot: `7d45aacb7d94c05410e3ac9e97ceba3a7734500d4a1881e4829e2d7fab70acf0`.
- Metric: national daily energy_generated, million_kWh.
- Study calendar: 1 January 2020–31 December 2023. The input archive also contains later years; all rows after 2023 are physically removed before calculations.
- Source eligibility and publication cutoffs reuse Release 1 definitions. Positive, finite original measurements with matching dimensions and source provenance only. Review-held values are excluded.
- No database connection, forecast fitting, canonical edits, validation/test reconstruction, or scoring against invented target values.
- Previously evaluated 2025 results remain unchanged. They cannot become a newly untouched final holdout.

## Mask design fixed before execution

Seed 20261108. Separate experiments with 1, 3, 7, 14 and 30 consecutive masked days. Request 20 windows per length, disclose actual counts if fewer are available.

Candidate blocks must consist entirely of eligible originals, lie within one training calendar year, start after 90 calendar warm-up days, and finish by 29 December 2023. Shuffle candidates per year using seed + length*100 + year; choose round-robin across years. Keep at least 28 unmasked calendar days between selected blocks. Hide all selected blocks simultaneously within each length experiment. Reset to original values between lengths. Imputed values are never donors.

For masked input date D, use a hypothetical target D+2 issued at noon Bangladesh on D+1. Every donor must precede D and meet the existing issue-time availability rule. Known late donors are refused; unknown historical publication times are explicitly assumed, not verified. This is a feature reconstruction scenario, not a claim about operational forecast performance.

## Fixed methods

| Policy | Donors | Minimum originals |
| --- | --- | ---: |
| Observed only | None; abstain | — |
| Recent original | Latest available original in D−1..D−3 | 1 |
| Previous week | Exact available original D−7 | 1 |
| Weekday median | Available originals D−7, D−14, D−21, D−28 | 2 |
| Past-year median | Available originals D−365..D−1 | 30 |

No future interpolation, global mean, backward filling, recursive estimates, or cross-year proxy filling for historically unreported metrics.

## Evaluation and provisional choice

For each length and policy report windows, masked dates, filled dates, coverage, known-time fillability, conditional MAE, RMSE and signed bias. Errors have the original million_kWh unit. Abstention has unavailable error, never zero error.

Also report errors on the intersection of dates filled by all four estimating methods. Compare errors and coverage together. Predefined provisional short-gap candidate: lowest pooled common-date MAE for lengths 1 and 3, tie broken by policy ID. Preserve (length,date) identities when pooling. This choice is exploratory training evidence, not automatic approval or a claim of superior forecast accuracy. Mask blocks favour complete stretches and do not identify real missingness mechanisms. No confidence interval or population-wide superiority claim is made.

## Actual-gap register and proposals

Classify absent/held training records using the frozen audit; include original source/version/hash and review flags where retained. Recovery status remains unassessed until actual source inspection. Missing canonical data does not prove an official PDF never existed.

Create unapproved feature-input proposals only where the original value is absent and an available original exists within the preceding three calendar days. Apply each estimating policy independently. Refuse held values and all other cases. Eligibility does not inspect a future gap endpoint or total eventual gap length. Proposals never become training labels, observed targets, or official measurements.

## Reproducible outputs and release gates

Produce study JSON, Markdown report, summary CSV, all masked trials, mask windows, original training calendar and actual input proposals. Store donor counts, date bounds, unknown-time counts and SHA-256 of ordered donor date/value/version/source tuples. Calendar + windows reproduce exact donor evidence. Record source and code fingerprints and per-export byte checksums.

Archive outputs with remote checksum verification in existing Drive storage, without changing collection checkpoints. Verify all masks are training originals, all donors precede reconstructed inputs, no held proposals, and zero model fitting/database writes. Publish authenticated read-only dashboard and downloads only after execution and tests.

Next decision after this delivery: assess whether to pre-register a downstream input-treatment impact experiment with chronological folds and original-only scoring targets. Do not reopen 2025 as an untouched test or optimize treatments against it.
