# Historical trends and comparisons

Implementation: 2 November 2026. Website `/analytics/comparisons`, authenticated API
`GET /api/v1/analytics/comparisons`. No migrations, new dependencies or secrets required.

## Scope and definitions

- Current validated national records, with original-source links and repeatable-read
  request snapshots. No database writes, repairs, imputation, forecasts or causal claims.
- The seasonal measurement selector supports the existing nine generation/demand/energy
  metrics. It controls seasonal profiles, year summaries, heatmap and monthly-change table.
- The generation-demand pair selector independently chooses day or evening peak in MW.
  The resolution selector controls that paired timeline: daily, monthly or yearly.
- Date filters are inclusive and clipped to known canonical-history bounds. Up to 10,000
  calendar days per request; narrow the date window if that guard is reached.
- Years select only the seasonal displays and tables. The paired timeline retains all
  dates in the selected date window. Default: latest three years in that window; up to eight.
  If explicitly selected years lie outside the date window, seasonal results can be empty.
- Missing fields remain null. A zero is an observed numeric zero, not missing data.

## Calculations

### Paired generation and demand

For each operational date with both compatible non-null peak measurements:

`difference_MW = reported_demand_MW - reported_generation_MW`.

Period generation, demand and signed-difference means use exactly the same matched
daily dates. Never subtract two means from different availability samples. Negative
differences are retained, not clamped to zero. A period with no paired days has null
values for all three series. Calendar gaps appear as gaps in daily charts.

Paired coverage = 100 × paired days / calendar days in the selected period slice.
Complete means every day in the whole calendar day/month/year has a pair and the whole
period was selected. Partial/sliced periods remain descriptive and marked incomplete.

This difference is **not recorded load shedding**, an energy quantity, proof of unmet
demand, or an attribution of causes. Comparability of source definitions needs PDF review.

### Seasonal profiles, heatmap and selected-year summaries

- MW: arithmetic mean of observed daily values. Annual means are weighted by observed
  daily counts, not equally weighted averages of monthly means.
- million kWh: sum of observed daily energy. Incomplete sums are not estimated complete
  month/year totals; a partial year's sum is not a full-year production estimate.
- Missing months/years stay blank. Heatmap cells display exact derived decimal values
  and observed/calendar counts. Underlines: green complete, amber partial/sliced, grey null.
- Heatmap intensity scales only across the displayed measurement's observed cells;
  colours are not comparable between different metrics, units or filter selections.
- Profiles are observed patterns, not a fitted seasonal model or significance test.
- Source-record links carry inclusive period dates and the relevant metric(s).

### Month-on-month and year-on-year changes

MoM baseline is the previous calendar month. YoY baseline is the same calendar month
in the previous year, not the previous observed row. Baselines must lie in the selected
date window, but can be outside the years selected for display.

`percent_change = 100 × (current_period_value - baseline_value) / abs(baseline_value)`.

Only show a percentage if both months are fully selected, every calendar day has a
non-null compatible measurement, and the baseline is nonzero. Otherwise return null
with an explicit status: current incomplete/sliced, baseline incomplete/sliced, baseline
outside window, zero baseline, or unavailable. Zero-baseline percentages are undefined.

Changes use the reported six-decimal derived period values. They do not extrapolate
incomplete observations. Energy total comparisons retain calendar-month length effects,
including leap February; they are not normalized changes in average daily energy.

## Source-quality warnings

Current screening candidates remain included in all selected canonical observations.
The warning counts generation/energy screen dates in the date window, independently of
the selected seasonal metric or year checkboxes. Its count does not certify demand,
temperature, cost or other fields, and is not a number of established extraction errors.
Follow the Measurement review link to inspect exact source evidence before research use.

The request fingerprint combines input record fingerprints, screen fingerprint and
comparison settings. It is not an immutable stored research dataset or a model version.

## User acceptance tests — live website

Use the authenticated production site; both Vercel projects must finish deploying.

1. **Navigation and loading.** Choose Trends & comparisons in the sidebar, or the new
   button on Generation & demand. Expect real counts, two charts, heatmap, year summaries
   and exact period tables. No sample values or replacement data should appear.
2. **Default paired chart.** Keep Evening peak and Monthly. Expect Generation, Demand
   and Demand minus generation legend entries. All use MW and the same paired day counts.
   Click a legend entry to hide/show it, hover a point for values/coverage, and move the
   slider to zoom. Missing periods must not become zero.
3. **Known single-date comparison.** Set both dates to `2026-11-01`, choose Evening peak,
   and apply. Compare the reported generation and demand with Master dataset for that date.
   Calculate demand minus generation yourself; the displayed signed difference must match.
   On a one-day selection Monthly/Yearly periods must be marked incomplete/sliced.
4. **Legacy unavailable field.** Set both dates to `2020-01-04`, choose Day peak, and apply.
   Expect no matched pairs if the existing legacy record has no day-peak demand. Demand
   and difference must be unavailable, rather than invented zeroes. Seasonal day-peak
   generation can still exist because it is a separate measurement.
5. **Resolution.** Reset, then change the paired view Monthly → Daily → Yearly.
   The number of periods/labels should change; paired daily-date count and overall mean
   difference must remain the same for the same date window/pair. Daily table pagination
   should preserve metric, pair, dates and year choices.
6. **Energy units.** Choose Energy generated for the seasonal measurement. Expect million
   kWh, observed monthly/yearly sums, and a warning about incomplete totals. The separate
   generation-demand chart must remain in MW. No automatic comparison of unlike units.
7. **Year selection.** Reset. Select two available years and apply. Seasonal profile
   legends, heatmap rows, year summaries and monthly table must show those years only.
   Paired timeline and its counts must retain the date-window scope. With no years checked,
   expect the latest three available years. More than eight yields a clear filter error.
8. **Heatmap and provenance.** Hover an amber cell: expect its exact value, observed-day
   count and incomplete status. Click it: Master dataset must show that cell's date range
   and selected metric. Blank cells must be labelled unavailable/outside window, not 0.
9. **Percentage safeguards.** Find a complete current month and complete baseline in the
   monthly table. Check `100*(current-baseline)/abs(baseline)` to six decimals. A missing,
   partial, sliced or zero baseline must instead show a dash and its reason. Filtering
   to a small portion of a month must withhold changes even if every selected day exists.
10. **Annual summaries.** Inspect observed/calendar counts and partial-year labels. For
    MW, verify against the average of the underlying daily records; do not average months
    equally. For energy, compare with the sum of the available daily energy records.
11. **Quality warning.** Open the measurement-review link. It must preserve the date
    filters and show generation/energy screening evidence. Viewing comparisons must not
    repair, remove, promote or exclude any canonical records.
12. **Invalid and empty filters.** Reverse the dates: expect a date-validation message.
    Choose a range beyond known history: expect an empty-state message with no invented
    data. Reset should restore the default full-history comparison.

## Optional local checks — Windows CMD

From the project root after pulling the update (resolve local changes before pulling):

```bat
set "PYTHONPATH=%CD%\backend"
.\.venv-recovery\Scripts\python.exe -m ruff check backend
.\.venv-recovery\Scripts\python.exe -m pytest -q
cd frontend
npm run test
npm run typecheck
npm run build
```

To run locally, keep the API and frontend in separate terminals using the established
private environment files. No credentials need to be pasted into the browser or GitHub.

## Automated coverage and limits

Backend tests cover matched-day intersection, null/zero/sign behavior, exact calendar
lags, completeness gates, zero baselines, energy sums, observation-weighted annual MW
means, leap dates, slicing, exclusions, fingerprints, authentication and no-store headers.
Frontend tests cover year/date/page filters and null/zero/coverage preservation in chart
inputs. Production browser acceptance is separate from these tests and is recorded in
the delivery notes. A PostgreSQL integration test remains opt-in; SQLite cannot establish
production transaction/locking behavior. No model or inference module is introduced.
