# Release 1 execution protocol

Fixed before the hosted run, 5 November 2026. Primary target: national daily
energy generated, million kWh. Existing source values and all calendar gaps remain
unchanged. This release reads Neon once and freezes the original snapshot and audit.

## Study and timing

- Study: 2020-01-01 through 2025-12-31. Full-history metric/year coverage is recorded
  alongside the experiment; the complete 2024 descriptive example is not the entire
  modelling sample.
- Training: 2020–2023. Internal selection: expanding training origins at 2021, 2022,
  2023, each evaluated across its full calendar year. Every fold fits once, using
  labels no later than two days before its first target.
- Validation: 2024; selected configuration fitted through 2023-12-30, then fixed.
- Test: 2025 reserved. Test outcomes are absent from modelling series, feature exports,
  predictions, metrics and hyperparameter selection. Frozen raw input retains the
  original records for a later separately authorized evaluation; this is reservation,
  not encryption or a claim that the data have never been viewed.
- Issue: noon Asia/Dhaka on T-1 for target T. Original day D is assumed reported at
  noon D+1. Latest permitted original input is T-2, not incomplete energy from T-1.
- Historical available_at is often unknown. Unknown times are explicitly assumed in
  the retrospective scenario; known late records are refused. Strict publication-time
  feature coverage is calculated separately. No verified point-in-time or live-accuracy
  claim is permitted when timing cannot be established.

## Models and selection

Benchmarks are the latest eligible report at exact calendar lag 2, and the same
weekday at lag 7. Neither fills a missing donor. Learned model: StandardScaler plus
Ridge, solver SVD. Lag 2/7/14/28, past-only 7/28-day means ending at T-2, and known
weekday/year sine/cosine features are the only inputs.

Ridge alphas: 0.1, 1, 10, 100. Input policies: complete rows; preceding original donor
within three days; exact original t-7 donor. Only missing INPUTS are treated. Original
training labels remain unfilled; held labels are excluded. Donors are never recursive,
never future values, and retain the reporting cutoff. A fixed chosen policy can be
used for validation-time inputs without using the validation target or fitting
transformations on validation rows.

All twelve candidates use identical common dates within each training fold. The
minimum of ten common dates per fold is an explicit engineering execution floor,
not proof of statistical adequacy. Selection uses pooled common-date training-fold
MAE, with deterministic policy/alpha tie-breaking. Scaling is fitted within each
training fold. Validation does not select or retune these choices.

Validation compares all three final forecasts on identical observed, unheld target
dates, with MAE, RMSE and signed mean error (prediction minus actual). Separate own-date
scores and forecast/scoring coverage prevent selective forecasting from hiding
failures. Actual missing/held targets stay unscored; predictions never replace them.

## Missing-input experiment

Seed 20261105. Twenty nonoverlapping training blocks per length 1, 3, 7, selected
from observed unheld training segments, with seven-day separation. Policies may
abstain. Report filled/masked coverage, conditional MAE/RMSE and the common filled
dates for the two donor methods. Observed-only abstains; it has no invented zero error.
Masking does not diagnose the actual missingness mechanism. Do not rank conditional
errors without coverage/common-date context or claim reconstruction equals forecasting.

## Execution and retained evidence

One online command: `python -m research.release1 --online` with PYTHONPATH=backend.
The GitHub workflow BPDB Release 1 experiments uses existing private Drive/Neon
secrets. No database or collection-checkpoint writes occur. It preserves frozen
input, model coefficients/scaling, training/validation features, validation predictions,
training selection, experiment JSON, a readable execution/test report and checksummed
manifest in Drive, with 30-day GitHub diagnostic artifacts.

Offline reproduction: `python -m research.release1 --bundle frozen_input.zip`.
The experiment fingerprint excludes the full-history readiness timestamp and ZIP
container byte identity, while retaining the canonical snapshot, protocol, source-code
hash, runtime and numerical results. A saved JSON linear model must reproduce sklearn
predictions within 1e-8. No pickle is loaded by the website.

The research environment pins NumPy, scikit-learn, SciPy, joblib and threadpoolctl.
These packages run in the worker; the website serves verified frozen results and
does not need to train in a web request. Source correctness, historical revisions,
cross-layout comparability and unmeasured errors remain limitations.

References: scikit-learn Pipeline/common-pitfall guidance and time-ordered evaluation:
https://scikit-learn.org/stable/common_pitfalls.html and
https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html.
