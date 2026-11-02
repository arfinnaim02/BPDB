# Generation and demand descriptive analytics — November 2, 2026

## Scope and access

The protected GET /api/v1/analytics/generation-demand powers the signed-in /analytics page.
The sidebar now includes Generation & demand. The existing Neon canonical records remain authoritative.
No migrations, ingestion changes, values, source files or forecasts are written by this feature.

Supported measurements:
- day/evening peak generation, evening peak demand, maximum generation and energy generated:
  supported by both existing parser families;
- day peak demand, minimum generation, energy demand and energy unserved:
  supported by the modern parser.

These are parser capability declarations, not claims that every historical PDF contains a field.
Actual non-null availability is calculated for the requested window. No source layout is inferred
from a hardcoded 2025 date cutoff. Original-PDF verification and source-gap causes remain separate.

## Filters and date bounds

Query parameters: metric (one of the nine supported names), resolution (daily/monthly/yearly,
default monthly), start_date/end_date (optional inclusive ISO dates).
The selected window is intersected with the known overall canonical-history bounds. Dates outside
those bounds are not declared missing. A non-overlapping window returns no effective bounds/points.
A missing date inside those bounds is retained, not interpolated or replaced with zero.

All returned current versions are validated national_daily records; other grains, regional
observations and superseded/nonvalidated versions are excluded. Metric units and period dimensions
must match the defined measurement. Ambiguous rows, nonfinite numbers and missing source membership
fail closed with a generic 503 rather than being silently merged.

## Aggregation and completeness

- MW: monthly/yearly main values are arithmetic means of observed daily measurements, never MW sums.
  For maximum_generation this is the mean of daily maxima, not a monthly single maximum.
  Minimum/maximum DAILY observed values are also shown separately.
- Daily energy (million kWh): monthly/yearly main values are sums of observed daily energy.
  They are not estimated full-period totals when observations are missing.
- Summary statistics always describe available DAILY observations, independent of chart resolution.
  The overall mean is weighted by observation count, not an unweighted mean of monthly means.
- Null or absent observations remain unavailable. Observed numeric zero is counted as a real value.
- Empty groups have null values/totals, not zero. Sample standard deviation is null for fewer than
  two observations and describes spread, not forecast uncertainty or an independent-observation CI.
- Derived statistics use Decimal arithmetic with 50-digit working precision and six-decimal half-even
  output rounding. Source observations are not rewritten.

Each period includes observed/canonical/expected calendar days. Boundary periods and date-filter
slices are explicitly marked. complete_period requires a full calendar period to be selected AND
a value for every expected date. A period with 100% observed coverage of a clipped window is still
a window slice rather than a complete month/year.

## Website

Apache ECharts history chart supports zoom and hover. Missing buckets break the line, no smoothing
or interpolation is enabled. Amber points denote incomplete periods or window slices.
The plot uses JavaScript numeric coordinates; exact returned decimal strings remain in the table.
The table displays 50 periods per page, but the chart/summary use the complete selected window.
Period links open Master Dataset with the same date range and selected measurement.

The request data fingerprint hashes selected current version IDs, dates, metric dimensions, source
IDs and values. It is independent of display resolution, but is not a persisted DatasetVersion,
a frozen analytical snapshot or an evaluation artifact.

## Limits and validation

At most 10,000 chart periods are returned. Use a narrower range or coarser resolution when needed.
Data requests use the existing read-only repeatable-read session, timeout and no-store policy.
The endpoint uses a canonical-date query and selected-measurement query with source-link checks.
No API key is sent to the browser; the website retains existing workspace authentication.

Local checks: 84 backend tests passed, one dedicated PostgreSQL test skipped; 7 frontend tests,
Ruff, TypeScript, Python compilation, dependency checks and the Next.js build passed.
Tests cover null/zero, missing days, leap months, window clipping, energy sums, MW means, weighting,
precision, canonical/version scope, dimension/provenance integrity, fingerprint and authentication.

Production data, original-PDF agreement, client chart rendering and Vercel runtime acceptance must
be checked after deployment. Browser QA status for this update will be reported separately.

## Live acceptance

Wait for both Vercel projects to deploy the new commit; no environment or migration changes needed.
1. Open Generation & demand. Default: day peak generation, monthly history.
2. Select a known short date range and daily resolution. Compare exact values with Master Dataset.
3. Select a range containing a known gap: it must remain a missing chart point and a blank table value.
4. Select energy generated, monthly resolution: observed sums and partial-period labels must appear.
5. Select day peak demand in 2020: unavailable values must remain blank, not estimated or zero.
6. Use chart zoom/hover, switch resolutions and navigate the period table.
7. Open a period's source-record link and verify its date filters.
8. Check desktop/mobile layout and runtime logs; a frontend 404/API failure while only one project
   has deployed is not successful acceptance.

Next: original-source verification and validated historical interpretation, then cost analytics and
forecast-target feasibility. This update does not approve the dataset for forecasting or claim that
all calendar gaps are caused by missing official reports.

Chart implementation references:
- https://echarts.apache.org/handbook/en/how-to/chart-types/line/basic-line/
- https://echarts.apache.org/handbook/en/concepts/chart-size/
