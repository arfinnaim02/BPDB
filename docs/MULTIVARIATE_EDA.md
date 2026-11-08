# Multivariable descriptive and exploratory analysis

Implementation: 8 November 2026. This extends the live analytical workspace; it does not refit, replace or rescore the frozen forecasting study.

## User workflow

1. Open Explore data and select one to eight distinct variables from thirteen supported national measurements.
2. Use a preset or choose variables individually; optional inclusive dates are clipped to current canonical history.
3. Read all-variable complete-case counts and each variable's own coverage before comparing results.
4. Choose Descriptive summary, Relationships, Distributions, Time patterns or Missingness & data.
5. Select a focus variable; choose independent scatter X/Y axes and Pearson, Spearman or first-difference matrix mode.
6. Download original aligned daily CSV, full descriptive statistics CSV, paired-relationship CSV, complete analysis JSON and individual SVG charts.

Single-variable analysis remains at `/explore/single`.

## Data and supported variables

The protected endpoint `/api/v1/analytics/exploratory` reads a single repeatable-read/read-only canonical database session. It supports the nine existing generation/demand variables plus maximum temperature, gas supplied, total production cost and production cost per kWh. Fuel/period/unit dimensions remain explicit; national all-fuel cost is not duplicated from component rows. Celsius CV is intentionally unavailable. Modern-only fields have shorter and different history.

Selection: one to eight distinct allowlisted variables; at most 10,000 calendar days; 3.5 MB hosted response guard. Invalid dates, duplicates and unsupported variables are refused. Duplicate/wrong-unit/wrong-period/unlinked measurements fail closed instead of silently selecting one. The API never writes Neon, fills targets, modifies original values or changes experiments.

## Statistics

Each variable reports observed/missing/zero/negative counts, coverage, longest missing run, mean, median, minimum, maximum, range, sample variance/SD, 5th/25th/75th/95th percentiles, IQR, Tukey fences/whiskers, outside-IQR count, positive-mean ratio-scale CV, adjusted skewness and adjusted excess kurtosis.

- Quantiles: type-7 interpolation at `(n-1)*p`.
- Sample variance: sum squared deviations divided by `n-1`.
- Skewness: bias-adjusted Fisher-Pearson, n>=3 and positive variance.
- Kurtosis: adjusted Fisher excess kurtosis, n>=4 and positive variance.
- CV: `100 * sample_SD / mean`, only positive means; not supplied for Celsius.
- Tukey: fences Q1 - 1.5 IQR and Q3 + 1.5 IQR; whiskers stop at extreme observations inside fences. Candidates are not confirmed errors.
- Decimal summaries: six decimal places, half-even; original aligned values retain their decimal strings.

No normality, independence, missing-at-random, significance, causal effect or prediction interval is inferred from these statistics.

## Relationships

Pearson and average-tie-rank Spearman use each pair's available same-calendar-day observations. At least three pairs and nonconstant inputs are required; this engineering floor is not a statistical adequacy guarantee. Undefined coefficients are null, not zero. Both coefficients and sample-size matrices are provided. Pairwise deletion can yield different date sets and a non-positive-semidefinite matrix.

First-difference Pearson requires both variables observed on the current AND previous calendar day. No compression to previous observed rows. Calendar-lag associations use exact lags 1-30 and separate pair counts; these are not a classical missingness-adjusted ACF, significance test or forecasting evaluation.

Scatter fits are descriptive OLS lines recalculated for the selected axis direction; no model selection, future prediction or uncertainty band. Coefficients use all eligible pairs. To bound SVG rendering, scatter draws at most 2,000 evenly spaced retained pairs and discloses displayed/total counts. Sampled chart points do not change numerical correlations.

## Twelve chart configurations

- Multivariable standardized timeline or original-unit focus timeline.
- Selected bivariate scatter and descriptive line.
- Pearson/Spearman/first-difference relationship heatmap.
- Pairwise sample-size heatmap.
- Standardized variable boxplots.
- Focus-variable histogram.
- Pooled month-of-year boxplots with counts.
- Weekday boxplots with counts.
- Exact calendar-lag association chart.
- Calendar-day first differences.
- Variable-by-selected-month availability heatmap.
- Focus year/month observed-mean heatmap.

Display standardization uses selected-window observed means/sample SD. It is exploratory, not a train-only transformation. Grouped means/boxes use available subsets; months, weekdays and years may have different sample composition. Availability denominator is selected calendar dates in each month, distinct from the single-variable studio's full-month coverage convention. Heatmap means are not full-month totals.

## Reproducibility and exports

An analysis ID binds the selected aligned values, variable metadata, methods, statistics, relationships, lag summaries and source fingerprint; generation time is excluded. JSON includes unique date/version/source lineage triples. The analysis is live and not automatically persisted; retain the JSON with its ID when citing it. CSV names include the analysis ID. Original-source drill-down remains in Master dataset. Chart numerics are display floating-point approximations; backend statistics use Decimal arithmetic.

## Verification

- Backend full suite: 301 passed, one optional PostgreSQL test skipped; Ruff passed.
- Frontend: 43 tests passed; TypeScript and production build passed.
- Independent checks: 36 comparisons against NumPy/SciPy for mean, median, quartiles, sample SD, adjusted moments, Pearson and Spearman across four sample sizes.
- All twelve actual chart configurations rendered SVG at 360px and 900px widths; null gaps and first-difference behavior verified.
- Isolated authenticated HTTP acceptance covers multi-variable and date selection, malformed/duplicate input, empty metric, preserved single-variable workspace, dataset/quality routes, authentication and API calendar alignment. Synthetic test observations are local-only, not deployed data.
- A separate Windows-hosted read-only acceptance workflow verifies eight real Neon variables, sample counts, source identity, artifact checksum, response size and independently recomputed Pearson coefficients. Its execution result is reported separately; do not infer real-data acceptance from local tests.
- Full authenticated browser/mobile visual-interaction acceptance remains unverified. Server-rendered SVG and HTTP checks do not substitute for browser interaction tests.

## Hosted acceptance — 8 November 2026

Run: https://github.com/arfinnaim02/BPDB/actions/runs/42449442596 — succeeded.

- Actual canonical window: 2019-10-19–2026-11-04; 2,574 calendar days.
- Generation, evening generation and evening demand: 2,390 observations each.
- Temperature, gas, per-kWh cost, total cost and energy unserved: 629 each; all-eight-variable complete dates: 629.
- 36 unique pairs including diagonals checked against aligned original data. Defined Pearson coefficients independently recomputed with Python statistics.correlation.
- JSON size 947,039 bytes; execution 4.38 seconds; database writes zero.
- Analysis ID: `dcf1417daf7a0f53664572e8e5d07a26c5c8e2dfbbc17d1173b196ed0ff93142`.
- Downloaded acceptance ZIP SHA-256 `c2e658d21a99f3d6bb06eb14f8954cce7c71d1143770920444b36a5f0e1c8fdb` verified, then analysis-file checksum verified against the acceptance record.
- Actual-data correlation, boxplot and scatter SVGs rendered; boxes changed to a horizontal layout and large-number ticks compacted to keep labels readable. Exact values remain in tables/JSON.
- Hosted numerical acceptance does not certify original-PDF accuracy, publication timing, causal interpretation or browser interaction behavior.
