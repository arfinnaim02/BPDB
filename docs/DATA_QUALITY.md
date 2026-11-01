# Full-history metric coverage and calendar gaps

## Scope

GET /api/v1/dataset/quality is protected by the existing X-API-Key dependency.
It reads every current validated national_daily canonical record. Superseded versions,
other grains, regional observations and partial/quarantined/conflicting current versions
are excluded. This is an availability report, not an independent source/value validation.

The frontend /quality page now uses this endpoint instead of downloading the latest 100 dates.
It retains signed workspace sessions and server-only API credentials.

## Definitions

- Calendar span: inclusive earliest to latest canonical operational date.
- Calendar coverage: canonical date count / calendar span days, multiplied by 100.
- Calendar gap: date inside those bounds with no current validated national_daily record.
- Yearly calendar span: intersection of that year with the overall observed bounds. First/last
  years are not assumed complete calendar years. Entire missing intermediate years remain visible.
- Metric availability: distinct canonical dates with at least one non-null observation for the
  metric/unit/period/fuel combination, divided by canonical dates in the selected year or all history.
- Unavailable metric dates: canonical dates minus dates with a non-null observation; includes absent
  rows and explicit nulls. This can include fields not supported by older document layouts.
- Zero dates: distinct dates with an observed numeric zero. Zero is counted as available.
- First/last value dates: earliest/latest non-null observation dates over the complete history.
- Empty denominators: percentage is null, displayed as a dash, rather than an invented 0%.

The 13 supported Page 1 metric definitions remain visible even when a field has never been observed.
Additional observed dimensions are shown separately. Different units/periods/fuels are never combined.
Duplicate presence on a date cannot inflate availability above 100%; deduplication of presence does
not certify the underlying values or resolve source conflicts.

## Gaps and pagination

Contiguous missing dates are returned as inclusive ranges, oldest first, with their day counts.
The sum of those counts equals missing_dates. The API accepts gap_page (1–100000) and
gap_page_size (1–100, default 20). The website offers 20/50/100 ranges per page.
Out-of-range pages return empty items without changing totals.

Each gap is marked missing_canonical_record with source_report_status=not_assessed.
No official report is declared missing, and no failure/quarantine/source-conflict cause is inferred.
Dates before the first or after the latest canonical record are not counted as gaps.
The metric-year selector changes the metric table only; gap reporting always covers full history.

## Consistency and performance

The endpoint reuses the existing read-only repeatable-read PostgreSQL session and statement timeout.
It uses two SELECT statements: ordered canonical dates, then a grouped union over measurement tables.
No per-date/year query loop, raw extraction text transfer or whole-record pagination is needed.
Dates and metric aggregation are from the same request snapshot. Gap pages requested later may
reflect a subsequent canonical update. Responses are no-store and contain no private storage paths.

## Verification

- Backend: 57 tests passed, 1 opt-in PostgreSQL integration test skipped.
- Frontend: 4 tests passed, TypeScript and Next.js production build passed.
- Ruff, Python compilation and dependency consistency passed.
- Tests include empty history, more than 100 dates, null/absent/zero handling, leap days, year
  boundaries, an entire missing year, superseded/nonvalidated/regional exclusions, unit/fuel/period
  isolation, distinct-date counting, gap pagination, authentication and response serialization.
- No production Neon credentials were used. Browser/live acceptance remains required.
  The managed preview's existing Next.js CLI incompatibility has not been resolved by this update.

## Live acceptance

Wait for BOTH Vercel projects to deploy the same new main commit; the backend must expose the new
route before the frontend can load it. No migration or environment-variable changes are required.

1. Open /quality on the website and check that the badge says All canonical history.
2. Compare canonical count, date bounds and missing-date total with /api/v1/dataset/summary.
3. Sum calendar-year canonical/gap/day totals and check they match the overview totals.
4. For a chosen metric, compare all-history non-null counts with the sum across years.
5. Select a year and check the canonical denominator changes; units/period/fuel stay distinct.
6. Review an inclusive gap range against master records; gaps must be labelled as unassessed
   for official source availability.
7. Use gap pagination and verify global totals remain stable if the database has not changed.
8. Verify browser layout on desktop/mobile. Stop/restart or sign-in as needed after deployment.

The next research step is investigation of reported gaps/unavailable fields against source documents,
followed by measurement validation and model-target feasibility. This report alone does not approve
a dataset for forecasting.
