# Reproducible research preparation

Implemented 3 November 2026. Website `/quality/prepare`; protected read-only API
`GET /api/v1/dataset/preparation`. No migration, dependency or secret changes.

## Purpose and research gate

This freezes the CURRENT canonical database evidence and an explicitly configured
research candidate. It does not repair historical sources or certify a model-ready
sample. Start with source investigation and the observed-only baseline. Missing-data
causes, definition comparability and source accuracy remain unresolved until reviewed.

Choose one of the 13 national metrics, an inclusive study window, training-end date
and validation-end date. Required order: start <= train_end < validation_end < end.
Training includes its cutoff; validation starts the next day; test follows validation.
All calendar dates, including dates without canonical records, are retained. A window
must fit inside known canonical history and contain at most 3,660 days. Cutoff choices
are the researcher's responsibility; the page never invents an approved split.

## Two distinct series

- `original_value`: exact source-derived stored value, or null. Never changed.
- `prepared_train_value`: original unheld TRAINING values and, only if explicitly chosen,
  eligible experimental training estimates. Always blank for validation/test.
- `observed_target_candidate`: original non-null and no implemented review hold. This is
  NOT independently verified ground truth or final eligibility for model scoring.
- Evidence state distinguishes missing canonical date, absent field, explicit null and observed.
- Every row retains version/source/page, availability, method, reason, review flags and donor IDs.
- Original zeroes remain observed; zero unserved energy is a valid candidate. The existing
  energy screen holds zero generated energy for review without recoding it as missing.
- Existing national generation/energy screen flags hold the entire day's selected metric
  conservatively. Negative selected values are also held (except temperature). Flags are not
  error diagnoses. Other measurement errors may be unscreened. Original values remain exported.

## Optional previous-week candidate

`policy=observed_only` is the default and performs no estimation.
`policy=past_week_train_only` is an experimental deterministic sensitivity candidate:

1. Consider only missing TRAINING runs, no longer than the user-selected 1, 2 or 3 days.
   The limit is a configurable experiment setting, NOT a statistically established safe threshold.
2. Require usable ORIGINAL training observations immediately before and after the run.
   Leading/trailing runs, a run ending at the training cutoff and held rows are not filled.
3. Use the original observation at exactly t-7 CALENDAR days, in training and without a hold.
   Never use t+7, future numeric observations, recursive estimates, global averages or zero-fill.
4. Require a known donor `available_at` no later than the start of t+1 in Asia/Dhaka
   (explicit end-of-operational-day preparation cutoff). Unknown/late donors stay missing.
   Naive database timestamps are treated as UTC, consistent with the database timestamp convention.
5. Retain original null/state and record donor date/version/source and experimental method.
   Validation/test missing targets remain null; held-out values cannot affect training preparation.

The right-boundary requirement uses training-period observation availability to classify an
INTERNAL reconstruction gap; this is not an online forecaster for date t. Current canonical
revisions may not have existed at historical origins. Donor checks alone do NOT establish a
point-in-time backtest, feature availability at a particular horizon or safe training-label
eligibility. This method may produce zero estimates on live data when historical availability
is unknown/late; that is an expected refusal to guess, not a broken imputer.

No performance claim, best-method selection or MCAR/MAR/MNAR diagnosis is made. Compare
justified methods with realistic artificial masking patterns on chronological TRAINING folds,
then use validation for selection and untouched observed test targets for final evaluation.
Rebuild preparation independently inside each future rolling-origin training fold.

## Monthly targets

A monthly total appears only for additive energy generated/demand/unserved or total production
cost, when the entire calendar month is selected and EVERY day has an original unheld value.
Estimated training values never enter observed monthly totals. MW, gas rate, temperature and
unit cost are not summed. A month straddling split cutoffs is marked `crosses_split_boundary`;
it is not an authorized monthly-model target split. Incomplete or held months have blank totals.
No observed subtotal is presented as a complete month, annualized or scaled to full coverage.

## Download and reproducibility

Preview computes a SHA-256 snapshot ID over canonical JSON containing preparation/review rule
versions, full configuration and sorted original records with exact measurements and source
URLs/checksums. UI preview shows the first 30 days plus all selected months. The downloaded bundle:

- `daily_values.csv`: date, labelled/unit-bearing original value and prepared training value;
  numeric/date/blank cells, without evidence text mixed into the measurement columns.
- `daily_audit.csv`: every selected calendar date with split, evidence state, values, holds,
  method/reason, original lineage and donor lineage.
- `monthly_observed.csv`: full-month evidence, split crossing and eligible original totals.
- `original_snapshot.json`: all supported national observations and source evidence for the
  selected current canonical versions, including original raw text and availability timestamps.
- `manifest.json`: snapshot ID, rules/config, split/reason counts, limits and each other file's
  SHA-256 and byte length. Runtime creation time is outside the content identity.

The preview's expected ID is sent at download. A canonical change produces HTTP 409 and requires
refreshing the preview. Each request uses the existing repeatable-read/read-only transaction.
No mutations or migrations occur. The server does not persist bundles: DOWNLOAD to retain the
snapshot. This is a research data bundle, not a repeated project-code ZIP distribution.

An original snapshot can be used to reconstruct the ID: hash canonical UTF-8 JSON
`{"config": manifest.config, "original": original_snapshot}` with sorted object keys,
compact separators, and literal Unicode. Creation times do not define dataset identity.
Rule changes must bump the preparation/review rule version. Export member hashes detect file
changes; the snapshot ID identifies input evidence and configuration, not archive compression.
No dataset/model registry, original-PDF repair, source-review decisions, forecasting model,
statistical accuracy comparison or durable Drive archive of research bundles is implemented here.

## Manual acceptance tests

1. Open Research preparation. Expect four empty required date inputs, baseline policy and
   known-history bounds. No study window should be applied until you preview it.
2. Energy generated: from 2024-01-01, training end 2024-06-30, validation end 2024-09-30,
   to 2024-12-31. Preview baseline. Counts must partition calendar days in each split.
   All estimated-training counts must be zero. Original review-held values remain visible.
3. Download the bundle and inspect all five members above. Original and prepared values are
   separate. Validation/test prepared-training columns must be entirely blank.
4. Choose previous-week experimental policy with 1-day maximum, keeping identical dates.
   An estimate is permitted only with the exact original t-7 donor, timely known availability,
   a short internal training run and no review holds. Unknown donors must remain blank.
5. Check cost with a study window inside its observed history. Earlier absent fields remain
   absent, not extrapolated. Monthly totals must remain blank if a day is missing/held.
6. Inspect leap February 2024: all 29 days are needed. A partial month is never complete.
   Any month crossing a cutoff is explicitly labelled and cannot silently become a training total.
7. Reset. All four dates clear; baseline is restored; preview/download disappear.
8. Reverse/equal split dates, invalid dates or dates outside known history: expect validation
   or unavailable state, never invented values. Anonymous API/export requests must be rejected.
9. Re-preview an unchanged snapshot: same ID. Change policy/cutoffs: different ID. If canonical
   inputs change between preview and download, expect 409 rather than a silently different dataset.
10. Verify member hashes, retain the downloaded snapshot, and use Missing data / Source audit /
    Measurement review to investigate evidence before approving any treatment for the thesis.

Local Windows checks after pulling:

```bat
set "PYTHONPATH=%CD%\backend"
.\.venv-recovery\Scripts\python.exe -m ruff check backend
.\.venv-recovery\Scripts\python.exe -m pytest -q
cd frontend
npm run test
npm run typecheck
npm run build
```

## Methodological references

- [scikit-learn: data leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage):
  preprocessing and model selection must not use unavailable evaluation information.
- [Forecasting: Principles and Practice, practical issues](https://otexts.com/fpp3/practical.html):
  missingness and outliers require contextual investigation; daily series can have multiple
  seasonalities and moving holidays such as Eid. These references do not approve this specific
  weekly donor policy or certify its accuracy on BPDB data.
