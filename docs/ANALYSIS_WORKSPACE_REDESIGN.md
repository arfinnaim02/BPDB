# Analysis-first frontend redesign — 7 November 2026

## Delivered experience

- Shared visual refresh across existing routes: larger readable typography, navy/teal analytical theme, consistent panels, buttons, tables, spacing and responsive layouts.
- Grouped navigation: Analyze, Models & evidence, Data library, collapsible Advanced research, and Administration. Collection logs remain on Collection history.
- Rebuilt Overview: latest canonical date, recent observed energy coverage, prospective sample size, timeline/monthly/coverage views, frozen model-error comparison and task-oriented next steps.
- New `/explore` analysis studio over nine supported national generation/demand measurements. Inclusive date filters, all-history selection, line/bar timeline switch, SVG chart downloads and precision-preserving selected daily CSV.
- Six analytical views: daily timeline plus strict trailing seven-calendar-day mean; observed monthly sums/means; histogram; complete-month year profiles; monthly observation coverage heatmap; and weekday mean/sample-size profile.
- New `/insights` evidence-to-interpretation page: completeness, largest observed value with source drill-down, variation, forecast scope, limitations and follow-up questions. These are descriptive planning considerations, not operational alerts or optimization.
- Historical Final evaluation adds MAE/RMSE comparison and signed-bias charts. Existing study outputs, model choice, sources, authentication and individual evidence downloads remain.

## Calculation and integrity rules

The backend remains authoritative. The new studio requests daily observations from the existing protected canonical analytics API; no database writes or backend changes occur.

The studio is live exploratory data, distinct from review-held frozen modelling samples. Existing screening candidates can remain visible. The source/support disclosure points users to Data quality before research modelling.

- Null remains unavailable and zero remains a value. Missing observations break timeline lines.
- Seven-day means require all seven consecutive calendar dates observed; no future donors or imputation.
- Monthly energy bars sum only observed daily energy. MW bars average observed daily MW. Pale bars indicate incomplete full months or selected boundary slices; they are never represented as complete monthly energy totals.
- Year profiles include only fully observed calendar months. Monthly coverage uses full-month calendar days; a selected partial month therefore has reduced coverage.
- Histogram uses ten equal-width bins, with an explicit single-bin case for identical observations; the final bin includes its upper endpoint. Weekday means show available-date sample sizes and do not identify causal weekday effects.
- Browser-derived chart values use floating-point display calculations. The source table and daily CSV preserve original decimal strings; no canonical values or authoritative CSV exports are replaced.
- No cost/fuel/zonal scenarios or load-shedding forecasts are fabricated. Generation-minus-demand differences are not labelled recorded shedding. Historical sample SD and error scores are not forecast intervals.
- Latest retained forecast need not target tomorrow. Prospective scores remain separate from historical scores, with missing actuals unavailable.

## Verification

- 38 frontend tests passed, including seven new numerical/rendering tests.
- All six actual studio chart option sets rendered nonempty SVG at 360px and 900px widths, without NaN output.
- TypeScript and Next production build passed.
- 13 authenticated HTTP acceptance groups passed against isolated SQLite using 330 original retained 2025 energy observations plus the existing frozen model assets: Overview, studio, insights, final evaluation, collection, dataset, quality, report, inclusive dates, invalid dates, empty metric selection and authentication.
- No test fixtures are packaged or shown in production. Fixture source links are test-only.
- Timeline SVG from retained observations rendered and inspected separately.
- Full browser visual/interaction review could not run: the managed preview service passed unsupported `--host`/`--strictPort` arguments to Next.js. SVG server rendering and HTTP acceptance do not substitute for a full browser/mobile interaction test. Production signed-in visual acceptance remains required.
- Backend source and experiments are unchanged; prior 293-backend-test acceptance is not relabelled as a new backend rerun.

## User acceptance

1. Overview: verify real latest canonical date, recent coverage and separate historical/prospective model context; no collection run tables.
2. Explore data: choose energy, then an inclusive date range. Check six charts, line/bar switch, zoom, tooltip units and SVG download.
3. Select an incomplete month: pale monthly bar, incomplete profile omitted, exact observed/missing daily table and CSV preserved. Select an unsupported historical metric and require an empty state.
4. Inspect Planning insights: check dates/values against the selected source record. Read limitations; no cost, risk probability or dispatch promise should appear.
5. Final evaluation: MAE/RMSE and bias match existing retained numerical tables; no model retuning or revised test scores.
6. On mobile: inspect navigation expansion/collapse, chart resizing, table scrolling and source/download controls. Report any clipping with a screenshot.

This redesign improves exploration and interpretation. It does not complete the original cost/demand/zonal forecasting research or turn descriptive observations into validated decision rules.
