# Research readiness and measurement review

Assessment date: 2 November 2026. This is an implementation/research protocol, not a
claim of completed source validation, forecast accuracy or thesis findings.

## Findings and priorities

The platform has acquisition, incremental collection, canonical Neon data, provenance,
exports, monitoring, coverage reporting, source audit and descriptive generation/demand
analytics. User screenshots show 2,383 canonical dates through 1 November 2026, after a
2 November collection run. Collection time is distinct from the PDF's operational date.

The current bottleneck is independent measurement validation. Matching staged values
to extraction JSON proves consistency of import, not accuracy against a printed PDF.
Legacy and modern layouts support different metrics. Do not describe every unavailable
field as an extraction failure, or every missing canonical date as an absent official PDF.

### Specific unresolved evidence

The live master record for 4 January 2020 stores energy generated = 1 million kWh,
maximum generation = 8,397 MW, and raw text `Total Gen. (MKWH) : 1`.
Source URL: https://misc.bpdb.gov.bd/storage/daily_archive/4472page1.pdf
Source SHA-256: `24d48b47c247fe2990d6ee935680a5b1e129225aeeb85dce3943fa4d03780a6b`
Version: `b1a38d8c-cf59-42fa-8d0f-770466791642`.
This is a review candidate, not an established official or parser error. The official
download returned HTTP 503 in the inspection environment; its printed number was not
verified. Do not replace 1 with a guessed value or a neighbouring day's measurement.

A synthetic regression test demonstrated that the prior legacy regex could accept
`1` from `1 57.6`. That proves a software failure mode, not the cause in this PDF.
The new legacy_page1_v3 parser refuses split/malformed energy tokens and quarantines
them rather than joining digits. The two available local representative PDFs still
extract energy as 166.4 (30 November 2019) and 324.38721 (27 October 2026) million kWh.
These targeted examples are not a random extraction-accuracy estimate.

The deployed screen at approximately 23:00 Bangladesh time on 2 November checked all
2,383 available canonical energy/maximum pairs. It found 19 review dates: 18 below the
explicit 0.10 ratio heuristic and one below the reported minimum-generation energy
floor. Counts depend on the current records and rule version, not a frozen dataset.

The latter is 9 June 2026: stored energy 306.09336 million kWh, minimum 13,125 MW
(implied floor 315 million kWh), maximum 15,490 MW. Stored text agrees with those
numbers; their printed values and compatible definitions are still unverified.
Source: https://misc.bpdb.gov.bd/storage/daily_archive/page_1_20260610_20260610143323.pdf
SHA-256: `f4cc99ac5979bc3c6da4ff261d6b6acf568507bf6c331ad9fa3799394850cbc8`.
Do not label this as an official reporting error without inspecting the original.

## Implemented review queue

- Website: `/quality/review`; protected API: `/api/v1/dataset/measurement-review`.
- Only current validated national records; optional inclusive dates, bounded pagination.
- Generation/energy consistency rules and an explicit low-ratio heuristic.
- Source URLs, checksums, raw text (up to 1,000 characters per measurement), page and
  version IDs. This text is the stored extraction evidence, not a fresh PDF reparse.
- Flag counts are per date/rule, not inferred numbers of extraction errors.
- A fingerprint identifies selected records, screening inputs and rule version. It is
  independent of pagination but is not a persisted immutable research snapshot.
- No database writes, saved review decisions, automatic corrections or model exclusion.
- No flags does not certify accuracy. Temperature, demand, fuel, cost and regional
  measurements need their own definition-aware audit.

### Screening formulas (national_energy_screen_v1)

For daily energy E in million kWh, daily maximum Pmax in MW and daily minimum Pmin:

- Ceiling: U = Pmax × 24 / 1000. Review E > U + tolerance.
- Floor, when Pmin exists: L = Pmin × 24 / 1000. Review E < L - tolerance.
- Bound tolerance: max(0.1 million kWh, 0.001 × applicable bound).
- Low-ratio heuristic: 0 <= E/U < 0.10, only for positive Pmax.
- Compare daily minimum/day/evening generation against Pmax with 1 MW tolerance.
- Review non-positive core values, negative minimum, duplicate dimensions, wrong
  units/periods and missing version-source links.

The 0.10 threshold is a transparent triage choice, not an empirically validated BPDB
limit, a calibrated detector or a statistical significance test. Physical relationships
also require compatible generation boundaries and definitions in the original report.
The underlying values, units and definitions must be inspected before concluding error.

## Source verification and correction protocol

1. Take every flagged source plus a stratified sample of unflagged PDFs by year,
   layout and metric. Targeted extremes alone cannot estimate extraction accuracy.
2. Check file SHA-256, operational/reporting dates, printed value/unit and source page.
   Compare both the rendered PDF and extracted text; layout spacing can split numbers.
3. Record agreement, confirmed discrepancy, unreadable source or definition mismatch,
   with reviewer, time, checksum, version and metric. A durable review ledger is pending.
4. Fix only confirmed parser failure modes. Retain real operational extremes and zeroes.
5. Run regression tests; reparse affected sources into a separate batch and compare all
   changed metrics. The daily worker does not automatically repair already-linked history.
6. Stage a new version, verify measurements and lineage, and promote after conflict
   review. Preserve previous versions and PDF hashes; rerun exports and screens.

Do not run blanket historical promotion or alter canonical values from heuristics alone.

## Research gates, in dependency order

### Gate A: Verified variables and availability

- Finalize a data dictionary: definition, unit, grain, layout support, conversion, first
  available observation and publication/availability time for every candidate variable.
- Close confirmed parser discrepancies and document unresolved cases and official gaps.
- Keep unknown original publication times unknown. A historical retrieval timestamp does
  not establish when an operational measurement was available to a real-time forecaster.
- Distinguish retrospective operational-date backtesting from true vintage-data testing.

### Gate B: Frozen analysis dataset

- Export current canonical values from one repeatable-read database snapshot.
- Store immutable data plus manifest: source/version lineage, checksums, extraction/rule
  versions, filter/target definitions, units, exclusions and missingness policy.
- Retain calendar gaps; do not treat a previous observed row as the previous calendar day.
- Never substitute incomplete monthly energy/cost sums for full-month observed targets.
- Compare included/excluded coverage and unresolved-flag sensitivity. No claims that
  missingness is random without supporting evidence.

### Gate C: Target feasibility

1. Daily evening peak demand: evaluate as a candidate because it is supported across
   legacy and modern parsers. Confirm its definition is comparable across layouts first.
2. Next-month total production cost: still the intended primary research target, but
   first count complete, comparable months with reconciled cost definitions. Modern-only
   daily values do not automatically provide enough annual cycles or holdout months.
   Do not invent a minimum sample size or announce seasonal ML success in advance.
3. Zonal load shedding: defer until zonal observations and event/magnitude definitions
   are actually extracted and verified. National energy unserved is not zonal shedding.

If the cost target is too short/incomplete, document the limitation and explicitly
refine the research scope before presenting another target as the primary contribution.

### Gate D: Reproducible forecasting experiments

- Predeclare target, forecast origin, horizon, calendar frequency and availability lag.
- Freeze a final chronological test period; tune on earlier rolling-origin folds only.
- Fit imputation, scaling, feature selection and any learned outlier handling inside
  each training fold. No full-series interpolation or future observed predictors.
- Start with naive and seasonal-naive benchmarks where the corresponding calendar lag
  exists; compare a small justified statistical/regularized/tree model set.
- Shift lag/rolling features by the forecast information cutoff. Keep evaluation dates
  and horizons comparable; disclose dropped targets and unavailable benchmark lags.
- Report MAE/RMSE and suitable scaled errors with their train-only denominators. Do not
  rely on MAPE for zero or near-zero targets, or on R-squared as the primary forecast score.
- Assess residual dependence and interval coverage if producing uncertainty intervals.
  Descriptive standard deviation is not a prediction interval.
- Save data manifest, code commit, versions/seeds, fold definitions, predictions,
  baseline comparisons, metrics and limitations. No performance claims before execution.

### Gate E: Thesis and deployment evidence

- RQ1: verified acquisition, idempotency, lineage and ingestion failure/recovery evidence.
- RQ2/RQ3: actual eligible cost/demand experiments and honest benchmark comparisons.
- RQ4: implement only if verified regional data supports the question.
- RQ5: show conditional scenarios with assumptions, not unsupported causal or policy claims.
- Generate analytical PDF reports and thesis tables from frozen outputs; preserve
  chart units, coverage, data/code versions and source attribution.
- Operational tasks remain: known-URL replacement detection, durable review ledger,
  full historical backup/restore, failure notifications and sustained scheduler evidence.

## Methodological sources

These inform the protocol; they do not certify this dataset or justify the 0.10 heuristic.

- Hyndman & Athanasopoulos, Forecasting: Principles and Practice, 3rd ed.,
  [outliers and missing values](https://otexts.com/fpp3/missing-outliers.html): investigate
  unusual observations before replacing them; missingness mechanisms matter.
- Same authors, [forecaster's toolbox](https://otexts.com/fpp3/toolbox.html), especially
  time-series cross-validation: training observations must precede forecast targets.
- scikit-learn, [common pitfalls / leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage):
  keep test data out of preprocessing fits and model selection.
- pdfplumber, [official documentation](https://github.com/jsvine/pdfplumber): character
  positioning, extraction tolerances and visual debugging support layout-aware inspection.

## Acceptance after deployment

1. Sign in, open Measurement review, and confirm counts and rule version load from Neon.
2. Filter 2020-01-04 to 2020-01-04: inspect the stored energy=1, maximum=8397,
   low-ratio reason and exact PDF checksum. Confirm these values against the original PDF.
3. Change page size/date window; confirm pagination and source links stay scoped.
4. Confirm the master dataset and canonical pointers are unchanged by viewing the queue.
5. Separately verify updated daily-worker parser behavior on real new legacy sources.

Local checks are reported in PROJECT_STATUS.md. Live production acceptance and source
verification are separate from automated tests; no review or repair is inferred from CI.
