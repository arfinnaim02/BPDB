# Release 3 — locked final evaluation protocol

Predeclared 5 November 2026 before generating any final-year model scores. Release 1 and Release 2 outputs remain immutable historical releases.

## Fixed question and model

Evaluate national daily energy generation (million kWh) in 2025. **Primary model: autoregressive OLS**, selected using Release 2's training-fold rule. No model is selected or retuned using the 2025 outcomes. Ridge (alpha 0.1), Random Forest (depth 8), Gradient Boosting (depth 2), exact lag 2 and exact lag 7 are fixed references. Tree hyperparameters are exactly those retained in Release 2. A reference method scoring better does not authorize switching the primary model after the test.

Use the exact frozen input archive SHA-256 `bbcf319b97029d15a8180849b3f7ca218ef1e3ef7debf4ed01d32c511516c81a`, snapshot `7d45aacb7d94c05410e3ac9e97ceba3a7734500d4a1881e4829e2d7fab70acf0`, and Release 2 experiment `c22ee6e06c2e26c40ee4f1754c083760b3de585e03c70b59a95fa91457b8eac6`. Do not query a fresh Neon snapshot or change holds. The raw archive has always contained 2025 originals: this is a reserved evaluation, not a blinded experiment or a claim that raw data have never been viewed.

## Fit, forecasting and availability

Refit all four learned families once on eligible labels from 2020 through **2024-12-30**. Including the validation year after model choice is permitted; settings stay fixed. Train-only scaling and the same nine Release 1 features and original previous-week input policy apply. Do not train on any 2025 label or update parameters during evaluation. Save the fitted model and actual fit-row count/last label.

Evaluate every calendar target from 2025-01-01 through 2025-12-31. Issue noon Asia/Dhaka on T-1; the latest original input is T-2 under the existing assumption that day D is reported by noon D+1. Known late inputs/labels are refused; unknown times are explicitly assumed only in this retrospective scenario. Strict verified publication-time feature coverage is reported separately. Current canonical revisions are not a verified point-in-time archive.

Past original 2025 observations may enter features for later 2025 targets, with the same origin cutoff. This is chronological updating of inputs, not fitting on test labels. Future observations and the current target cannot enter features. Missing or held targets remain unscored and original gaps are never replaced by predictions. No clipping or other postprocessing is added.

## Locked scoring and sensitivity

- Primary comparison: OLS versus exact lag 2 on **identical observed dates where all six fixed methods forecast**.
- Report all-six common-date MAE, RMSE and signed bias (prediction minus observation), with per-model own-date scores, calendar forecast counts and negative forecasts. Own-date samples are different and cannot replace the common-date comparison.
- Retain all 365 calendar rows and report monthly scores on each month's common intersection. Monthly rows are descriptive, not model selection.
- Predefined uncertainty sensitivity: OLS minus lag-2 absolute-error difference on the all-six common dates. Use **paired circular calendar blocks** of 7, 14 and 28 days; 2,000 resamples each; Python random seed 20261105 plus block length; percentile endpoints 2.5 and 97.5 with linear interpolation.
- Draw starts uniformly over all 365 calendar rows, wrap within the year, concatenate/truncate to 365 rows, then score only matched target/forecast rows. Missing/unmatched rows travel with their calendar blocks; do not compress gaps into consecutive days. Record valid replicate counts and sample denominator.
- Negative point differences favor OLS. These are **descriptive dependence-sensitivity ranges**, not per-day forecast intervals, calibrated significance tests or proof of population superiority. Wrap-around, seasonal/nonstationary errors, one test year and the missingness mechanism limit interpretation. Do not choose block length after seeing outcomes or automatically declare significance.

## Once-only logical evaluation and evidence

The hosted workflow restores the same frozen archive from private Drive and commits to this protocol in Git before execution. It retains safe JSON coefficients/trees, final-year features, predictions, numerical checks, source hashes, runtime, report and manifest. No Neon or collection-checkpoint writes occur.

A private Drive final-evaluation receipt binds protocol/code key to verified result blobs. Subsequent hosted executions with the same key restore those results instead of fitting or rescoring. A different key is refused once a final evaluation has been retained. The shared workflow concurrency group prevents competing registry writers. If an interrupted run has not retained its receipt, an identical-protocol retry can reproduce the same logical evaluation; do not change settings after inspecting output. Offline reproduction is allowed for verification, not new selection.

Saved-model inference must match sklearn within 1e-8. Preserve held and missing targets; independently recompute final common-date scores and verify every manifest checksum before publishing. Statistical holdout evaluation under the disclosed historical timing scenario does not itself authorize an operational live-forecast claim.

## References and remaining work

- Forecast evaluation and training/test separation: https://otexts.com/fpp3/toolbox.html (Evaluating point forecast accuracy).
- Time-series block bootstrap forms and boundary behavior: https://bashtage.github.io/arch/bootstrap/timeseries-bootstraps.html.
- sklearn train-only transformations: https://scikit-learn.org/stable/common_pitfalls.html.

After this release, do not reuse 2025 as a fresh untouched holdout for later tuned models. Any further model development needs a new prospective evaluation or explicit exploratory labelling. The evaluated historical model, thesis methods/results, source limitations and future-deployment requirements must remain distinct.
