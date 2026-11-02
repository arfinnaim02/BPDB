# Missing-data assessment and treatment policy

Implemented 3 November 2026. Website `/quality/missing`; protected read-only API
`GET /api/v1/dataset/missingness`. No migrations, new dependencies or secrets are needed.

## What this step delivers

An assessment of all 13 supported national metrics: observed/zero days, unavailable
states, consecutive missing runs, leading/internal/trailing unavailability, observed
streaks, full-month availability and consecutive complete-month counts. The selected
metric has gap details and month-by-month evidence. Raw measurements remain unchanged.

This is the dependency before a prepared modelling dataset. It does not recover PDF
values, impute observations, save a treatment policy per record, remove outliers, train
a model, certify source accuracy or establish whether missingness is MCAR/MAR/MNAR.

## Evidence states, not inferred causes

Every calendar day in the selected scope belongs to exactly one availability state:

1. **Observed:** a compatible non-null metric value, including genuine numeric zero.
2. **No canonical record:** no current validated national version exists for that date.
3. **Absent field:** a canonical version exists but no matching observation row exists.
4. **Explicit null:** the compatible metric row exists with a null value.

The last three states partition unavailable days. A missing canonical record may be a
collection failure, quarantine, conflict or unavailable official report; its cause is
not inferred. An absent/null field may reflect parser capability, source format, missing
source content or extraction problems. It is not automatically a recoverable parser error.
Use the existing Source audit, local manifests and actual PDFs to investigate causes.

The implemented legacy/modern capability label is a parser description, not proof that
an older original PDF omits a field. There is no hard-coded calendar cutoff for layouts.
Numerically suspicious canonical values still count as observed until reviewed; this
page does not convert the Measurement review queue into missing values.

## Scope and formulas

- Canonical selection: current validated national versions, with the current-version
  pointer joined back to the same report. Superseded, held and regional records are excluded.
- Inclusive dates are clipped to the earliest/latest known canonical-history bounds.
  Dates before/after those bounds, including unpublished future days, are not assessed.
- A selected window entirely inside a historical canonical gap is assessed even when
  it contains zero canonical dates. An entirely non-overlapping window is unassessed.
- `calendar_days = end - start + 1`.
- `unavailable_days = calendar_days - observed_days`.
- `unavailable_days = missing_canonical_days + absent_field_days + explicit_null_days`.
- `calendar_coverage_percent = 100 * observed_days / calendar_days`; undefined with no scope.
- Every zero remains an observed value. Missing values never become zero.
- Unit, period, fuel, expected table, uniqueness and version-source provenance are checked.
  Inconsistent known metric rows cause a consistency error, rather than silently counting
  them as missing or joining incompatible dimensions.
- Assessment is bounded to 20,000 calendar days and 10,000 canonical dates per window.
  Three bounded read statements suffice when observations exist; there are no per-date
  database queries, raw PDF text fetches or database writes.

## Observed window and consecutive runs

A metric's observed window runs from its first through its last non-null value in the
selected date window. Leading and trailing days are counted separately from missing
days between those endpoints. If no values exist, there is no observed window, and its
leading/internal/trailing counts are undefined, rather than a fabricated zero-length window.

Runs are maximal consecutive calendar dates without a value, even when a run mixes
canonical gaps, absent fields and nulls. Each run includes counts of those three states,
its boundary position and an explicitly unassessed source cause. Runs at selected
window edges may be shortened by filters. Their positions describe this window only.

The displayed length bins (1, 2–3, 4–7, 8–30 and 31+ days) are descriptive, not thresholds
authorizing interpolation. Observed streaks use consecutive calendar days, not consecutive
rows after dropping missing dates. The latest observed streak must end at the window end.

## Complete-month assessment

For each supported metric, the report distinguishes:

- all months intersecting the selected window;
- whole calendar months selected;
- whole months with a non-null value on every calendar day;
- incomplete whole months;
- partial boundary-month slices;
- months with zero observations;
- longest consecutive run of complete months.

Leap years use their actual calendar length. A slice with 1/1 or 27/27 observed days is
not a complete calendar month. A complete month of reported zeros is fully available,
although its numerical validity still needs source review.

Completeness indicates availability only. It is not a minimum-sample-size rule, a target
feasibility certificate, a guarantee of compatible definitions or proof that cost/energy
totals have been validated. Incomplete monthly sums remain observed subtotals. Do not
annualize them or call them full-month training targets.

## Treatment policy for the next modelling step

1. Recover original source-supported measurements before considering estimates. Record
   confirmed causes and reviewer decisions; leave unverified causes unknown.
2. Keep layout/definition-related unavailable periods separate when choosing a defensible
   analysis window. Do not extrapolate a modern field across older years automatically.
3. Preserve original Neon values and nulls. A prepared dataset must retain an observed
   flag, method/version, treatment reason and original version/source lineage.
4. Compare justified missing-data strategies on chronological training/validation folds.
   No automatic zero-fill, global mean, blanket forward-fill or interpolation is authorized
   by a gap's short length alone. Past forecasts cannot use observations from their future.
5. Fit any learned imputer, scaling or other preparation only on the training fold. Missing
   lag predictors and missing targets are separate problems requiring explicit policies.
6. Evaluate against genuinely observed, quality-accepted held-out targets. Do not impute
   held-out target values and score against those estimates; disclose excluded targets,
   changed evaluation coverage and sensitivity to unresolved source cases.
7. Freeze the original and prepared snapshots, eligibility rules, checksums and experiment
   settings before comparing model performance.

This protocol permits methodological comparisons later; this implementation performs
assessment only. Missingness mechanisms and suitable estimators depend on evidence and
the specific target, horizon, information cutoff and evaluation design.

## API and fingerprint

Parameters: `metric` (one of the 13 fixed metrics), inclusive `start_date`/`end_date`,
`gap_page` (1–100000), `gap_page_size` (1–50), `month_page` (1–100000).
Gap pages are oldest first; month pages are newest first, 24 months per page.
Both pagers preserve metric and dates. The all-metric summary always covers the same window.

The input fingerprint covers all 13 metrics, canonical version identities, values and
dimensions plus the date window and assessment-rule version. It is independent of
selected metric/pagination; it is not a persisted immutable research dataset.

## Browser acceptance checklist

1. Open Missing data. Confirm all 13 metrics, selected-metric detail, gap distribution,
   gap table and month table load from Neon. The canonical-gap count must agree with
   Data quality for an identical full-history window.
2. Select Energy generated. Confirm unavailable days equal the three missing-state
   counts combined. Observed zeroes must be reported separately from unavailable days.
3. Select Total production cost. Inspect first/last values, leading unavailability,
   internal gaps, complete-month count and longest complete-month streak. Do not treat
   earlier unavailability as a confirmed source-layout cause or as filled cost observations.
4. Select a metric/window with no values, for example a modern-only field in legacy
   history. Expect no invented first/last date, undefined observed-window counts and
   a `No observed value window` run, not automatic backward filling.
5. Filter to a small slice of an observed month. Even if all selected days have values,
   expect zero complete months and a selected-month-slice label.
6. Inspect a known full month (for example February 2024 for core generation, subject
   to later corrections). Leap February must use 29 calendar days.
7. Advance gap and month pages separately. Confirm both preserve metric/dates and the
   other page. Click a range/month: Master dataset must receive its dates and metric.
8. Reverse dates: expect a clear filter-validation message. Select a range beyond history:
   expect no-overlap state. Reset must restore both visible controls and their data.
9. Open Source audit and Measurement review links for further investigation. Availability
   is separate from numerical warnings, original-PDF agreement and confirmed missing causes.
10. Confirm there is no Fill/apply-correction action and that viewing the report does not
    alter master records or source versions.

## Optional local checks — Windows CMD

After pulling the update and resolving any local changes:

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

- Hyndman & Athanasopoulos, Forecasting: Principles and Practice (3rd ed.),
  [outliers and missing values](https://otexts.com/fpp3/practical.html#dealing-with-outliers-and-missing-values).
  Investigate unusual observations and the missingness context before choosing treatment.
- scikit-learn, [data leakage and preprocessing](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).
  Keep evaluation information out of preprocessing fits and model selection.

These sources support methodological caution; they do not certify this dataset or
prescribe the displayed gap bins as imputation rules.
