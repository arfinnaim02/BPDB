# Release 4 — prospective saved-model research forecasts

## Defined scope

Use the exact saved OLS model evaluated in Release 3. Its model ID is SHA-256 of the canonical saved JSON; the final-evaluation ID remains linked. No refitting, new model selection or reuse of the final year as an untouched test occurs. These are research forecasts, not official BPDB measurements or verified operational guarantees.

Forecasts and later actual comparisons are stored in separate Neon tables. The master observations, canonical pointers, PDF archive and frozen Release 1–3 results remain separate.

## Honest issue time and input availability

After a successful daily collection and verified Drive checkpoint, capture a repeatable-read Neon snapshot and target the **next Bangladesh calendar day**. Store the actual issue timestamp. GitHub's noon schedule can be delayed; do not pretend a late execution occurred at noon.

The date cutoff stays T-2 and the input window is T-35 through T-2. Nine model features and the original previous-week substitution policy remain unchanged. Only missing/unusable feature inputs can use an exact original seven days earlier; no recursive donors or target imputation. Units, national/daily dimensions, numerical holds and source/version linkage are checked. Known timestamps later than capture are excluded.

Each used source/version must already exist in the captured platform snapshot, with creation/retrieval timestamps no later than capture. Capture precedes actual issuance. This is prospective evidence of platform availability, not verification of an unknown official publication timestamp or a reconstruction of historical availability. Freeze original values, source URLs/checksums, version IDs, eligibility reasons, chosen donors, feature values and linear contributions. Preserve unknown official timestamps explicitly.

Refuse unsafe/nonpositive output or insufficient donors and retain a **withheld** attempt with reasons. Do not fabricate a prediction. No confidence interval is invented. The saved model remains trained on 1,557 usable rows with last usable label 2024-10-18; age and historical-evaluation limitations remain visible.

## Immutable issues and revised outcomes

Database uniqueness on model/target/input fingerprint makes an identical rerun reuse its first issue and timestamp. A changed captured snapshot creates a new retained attempt, even if its numerical prediction is unchanged. Earlier attempts are never overwritten.

On subsequent runs, compare forecast targets only after their Bangladesh calendar day has ended. Retain each eligible canonical actual/source revision separately, with observed energy, signed/absolute error and source/version evidence. Actual observations remain unchanged. Automatic reconciliation is bounded to the previous 90 completed days, with a 2,000-attempt safety cap; older revisions require an explicitly scoped follow-up rather than silent historical rescoring.

The 90-day prospective summary uses the **earliest successful issue per model/target**, with its latest retained actual revision. Do not select a later forecast because it is more accurate. Report attempted target dates, target dates with a forecast and paired scored dates; empty MAE/RMSE/bias stay null. This is a new prospective log, not a backfilled historical forecast record.

## Operation and acceptance

Alembic 0003 adds only research_forecasts and research_forecast_outcomes. The daily workflow applies pending migrations before the forecast step. Collection/Drive failure skips forecasting; forecast infrastructure failure makes the pipeline need attention. A successfully recorded withheld attempt is a valid execution, not a manufactured success prediction.

The web API is authenticated and read-only. The worker owns inserts; the dashboard fetches fresh Neon forecast rows, so new forecasts/outcome comparisons do not need frontend redeployment. CSV and JSON downloads remain distinct from the authoritative master CSV.

Acceptance includes real PostgreSQL migration consistency, two identical hosted executions retaining one issue/time, unchanged counts in original source tables, saved inference arithmetic, explicit withheld cases, no future donor/capture, revision retention, earliest-issue scoring, authentication and numerical exports. Source-table count equality is an operational check, not an independent proof of every PDF value.
