# Pre-registration: chronological forecast impact of missing-input treatment

Version: **treatment_forecast_impact_v1**. Registration date: **8 November 2026, Bangladesh**. The registration becomes fixed at the Git commit containing this document and TREATMENT_IMPACT_PROTOCOL.json. No new forecast experiment or production retraining is started by this release.

## Research question and honest scope

Does replacing an unavailable **energy feature input** with a recent original improve the same model's forecasts, compared with the current previous-week original policy, without sacrificing prediction coverage?

This follows the completed training-mask reconstruction study. Its recent-original candidate was chosen using 2020–2023 masks. Therefore, subsequent 2021–2023 diagnostics are **retrospective and selection-exposed**, even with chronological fitting. Prior research also exposed 2024. None of those years is a new independent confirmation set. The already evaluated 2025 period is excluded from this experiment and cannot be reused to choose a policy.

A separate future shadow comparison is reserved below. Missing targets are never filled. The study concerns national daily energy, not historical temperature, cost or every thesis outcome.

## Frozen data and recovery gate

| Item | Identity |
| --- | --- |
| Frozen input ZIP SHA-256 | bbcf319b97029d15a8180849b3f7ca218ef1e3ef7debf4ed01d32c511516c81a |
| Snapshot | 7d45aacb7d94c05410e3ac9e97ceba3a7734500d4a1881e4829e2d7fab70acf0 |
| Treatment study | e83ad7c06caf768c72369a6d9d3c76492a80bb608eb58cbac630094a3e0aad6e |
| Target/unit | National energy_generated / million_kWh |

Investigate original PDFs before estimating absent data. Candidate discovery, a passing parse and physical source availability are not repair approvals. No current canonical record is replaced by this work.

The primary diagnostic keeps the original frozen snapshot for comparability. If original-source repairs are independently approved later, create a new source manifest/snapshot and run a separately identified sensitivity analysis with the same fixed settings. Keep old results and a date/value/source diff. Do not quietly inject corrections or newly available targets into the primary analysis.

## Stage A — controlled historical diagnostic

| Fold | Fit starts | Latest possible fit label | Forecast targets |
| --- | --- | --- | --- |
| Diagnostic 2021 | 2020-01-01 | 2020-12-30 | 2021-01-01–2021-12-31 |
| Diagnostic 2022 | 2020-01-01 | 2021-12-30 | 2022-01-01–2022-12-31 |
| Diagnostic 2023 | 2020-01-01 | 2022-12-30 | 2023-01-01–2023-12-31 |
| Secondary, previously exposed | 2020-01-01 | 2023-12-30 | 2024-01-01–2024-12-31 |

Fit exactly one **train-only StandardScaler + LinearRegression(fit_intercept=True)** per fold, using complete original feature rows and eligible original labels only. Require at least 60 eligible fit rows; otherwise the fold is unavailable, not silently altered. Freeze coefficients and fit-row identities before the fold's predictions.

Apply the same coefficients under all three inference policies. No hyperparameter search, intra-fold refitting, clipping or target transformation. This isolates the inference-input treatment effect from changes in training-row composition. Training each policy on differently imputed training rows would answer another question and requires a later protocol.

Features stay in the existing nine-feature order: lags 2, 7, 14, 28; mean of calendar lags 2–8; weekday sine/cosine; day-of-year sine/cosine. Preserve the dense calendar; a missing day never shifts a lag.

Issue time is noon Asia/Dhaka on T−1. Original input dates cannot exceed T−2. A replacement for requested input D must be an eligible original dated before D, with known availability no later than the actual target's issue cutoff. Estimates never become donors. Historical unknown publication times are assumed and counted, not portrayed as proven operational availability.

## Three fixed inference policies

| Policy | When a requested original input is unavailable |
| --- | --- |
| Observed only | Abstain |
| Previous-week original | Use eligible, available original D−7; otherwise abstain |
| Recent original | Use latest eligible, available original D−1..D−3; otherwise abstain |

Held input values are unavailable slots; their suspect numeric values are forbidden donors and labels. Filling an input slot does not clear the underlying source review.

## Outcomes and matched comparisons

**Primary contrast:** recent-original minus previous-week absolute forecast error, on dates both policies forecast and an eligible original target exists, restricted to dates with at least one originally unavailable required feature. Negative difference favours recent-original treatment.

Define that affected stratum from input availability **before** applying either policy, without using the target or forecast error. Report:

- Paired affected-date MAE difference and relative MAE change.
- MAE, RMSE and signed bias on all shared dates, own-policy dates and affected shared dates.
- Full-calendar forecast coverage, original-target coverage, affected-date coverage and abstention reasons.
- Per-fold/year/month counts and errors, replacement counts, donor ages, source fingerprints and unknown-time counts.

Own-date errors use different populations and cannot establish a winner on their own. Missing predictions have unavailable error, not zero error. On complete original rows, the three policies must produce identical forecasts; report this identity as an implementation check rather than an improvement.

For descriptive dependence sensitivity, use paired circular calendar-block resampling within folds, lengths 7 and 14, 2,000 replicates, seed 20261108, 2.5/97.5 percentiles. Retain unscored calendar rows and disclose invalid/empty resamples. These intervals are not calibrated prediction intervals or proof of causal superiority.

## Predefined diagnostic support rule

All conditions must hold to label recent-original treatment diagnostically supported:

1. At least 30 affected shared target dates overall, including at least 10 in each of two folds.
2. At least 5% lower affected-stratum shared-date MAE.
3. All-shared-date MAE does not worsen.
4. All-shared-date RMSE increases by no more than 2%.
5. Full-calendar forecast coverage drops by no more than one percentage point.

If the reference MAE is zero, relative improvement is undefined; report absolute errors and no automatic support decision. Report contrary folds and interval sensitivity. Passing this diagnostic rule never authorizes automatic production deployment.

## Stage B — reserved future shadow confirmation

**Planned target dates: 10 November–9 December 2026, inclusive (30 days).** First issue: **9 November 2026, 12:00 Asia/Dhaka**. This is a protocol reservation; no worker or schedule has been started.

Use the same existing saved OLS model, ID:
`04aac742dbd25a35070b86e12279e51a3e762099696399221cb8a23244a8a2f3`.

No fitting or coefficient changes. Both shadow policies must persist their predictions, exact source snapshots, version/value hashes, donor identities and capture timestamps **before issue**, in a separate append-only research ledger. Preserve the live forecast ledger and current production policy.

A source snapshot captured before issue proves platform possession of those bytes/values, not the official publication time. Refuse donors without defensible as-of-issue evidence. Do not backdate database availability fields.

For target T, lock the eligible original canonical target as of **T+7 at noon Bangladesh**, retaining value/version/source hash. No eligible original at that cutoff means unscored. Subsequent source revisions belong in a separately labelled sensitivity analysis.

Require at least 20 shared scored dates and 10 affected shared dates. Apply the same 5% affected-MAE, all-shared MAE/RMSE and coverage criteria. Insufficient affected dates mean **inconclusive or policy-equivalent**, not treatment success. A period with no missing inputs cannot establish the benefit of imputation.

Never reconstruct missed forecasts after their issue time. If the shadow implementation is not ready for the first issue, commit a dated amendment for a replacement period **before that period starts**. Do not extend the period automatically after seeing favourable/unfavourable errors.

## Execution and reporting gates

This registration does not run Stage A, Stage B, a scheduler or a production retraining job. The next execution release must implement and test the registered rules, freeze code/runtime hashes, and retain date-level outputs before any model-performance conclusion.

Required artifacts: protocol/commit/runtime fingerprints; fold row dates and coefficients; date-policy predictions/targets/donors; matched/own/affected score and coverage tables; bootstrap sensitivity; recovery snapshot diff if approved; and an acceptance report including negative/inconclusive outcomes.

Validate the registration without fitting anything:

```text
python -m research.treatment_impact_protocol
```

Expected: a protocol SHA-256, fixed date windows, zero models fit, zero database writes and null results. Any change to the design after registration requires a new version/commit and an explanation before the affected execution.
