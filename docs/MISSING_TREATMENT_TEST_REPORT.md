# Missing-Data Treatment Study — execution and acceptance report

## Outcome

A completed training-only energy-input reconstruction study is available at **/quality/treatment**, with authenticated tables, coverage/error charts and seven evidence downloads. No forecast model was retrained. No canonical measurement, missing target, held value, saved forecast or previous final evaluation was overwritten.

Predeclared protocol/code commit: [0b75a070](https://github.com/arfinnaim02/BPDB/commit/0b75a070c5628f32154e60b7411e26c91af9ca13).
An additional explicit hold-state safeguard was committed before the archived rerun: [4516b115](https://github.com/arfinnaim02/BPDB/commit/4516b1154e87645dd04c3ce43d21ec33c6976153). This protects even held rows with no retained value; the numeric results were unchanged.

Hosted real-data execution: [GitHub Actions 42453574916](https://github.com/arfinnaim02/BPDB/actions/runs/42453574916), successful. Foundation and backend checks at that commit also succeeded.

Study ID: `e83ad7c06caf768c72369a6d9d3c76492a80bb608eb58cbac630094a3e0aad6e`.

## What was studied

National daily energy_generated, million_kWh, from the existing frozen snapshot. The training calendar has 1,461 dates (2020–2023), of which 1,378 are eligible originals, 67 have no canonical record and 16 are review-held. These are frozen-study counts, not a live audit of every current variable.

The full source archive contains later years, but all dates after 2023 were physically excluded before treatment calculations. Unknown publication times remain an assumption. The study is not a proof that every historical donor was available to a live forecaster.

Requested 20 artificial windows for each gap length. Actual counts: 20 each for 1, 3, 7 and 14 days; 13 for 30 days. The 30-day count is lower because of the eligible-block and separation rules; it was not padded or silently relaxed. There are 890 masked date-experiment pairs, each evaluated under five policies: 4,450 trial rows. The same calendar date may occur in different length experiments.

## Main short-gap result

The predefined criterion pools shared filled dates from the 1-day and 3-day experiments. All four estimating methods use exactly 77 date-experiment pairs. Errors are in million kWh.

| Method | Shared n | MAE | RMSE | Signed bias |
| --- | ---: | ---: | ---: | ---: |
| Recent original, at most 3 days | 77 | 12.8485 | 17.7667 | 0.1399 |
| Original previous week | 77 | 22.1581 | 29.6915 | 1.6906 |
| Weekday median, past 28 days | 77 | 22.6600 | 29.2242 | 4.3743 |
| Median of past-year originals | 77 | 37.3282 | 42.7185 | 2.7633 |

**Interpretation:** recent-original treatment is the provisional short-gap reconstruction candidate under this fixed training mask design. This does not establish better forecasting, suitability for other variables, or superiority under all missingness mechanisms. No imputer has been automatically approved.

Observed-only abstains on every hidden date. It has 0% reconstruction coverage and unavailable MAE/RMSE/bias, not zero error.

## Why coverage matters

Recent-original performance changes with gap length:

| Artificial gap | Windows | Masked dates | Recent-original fills | Coverage | Conditional MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 day | 20 | 20 | 20 | 100.0000% | 6.2226 |
| 3 days | 20 | 60 | 59 | 98.3333% | 14.8065 |
| 7 days | 20 | 140 | 58 | 41.4286% | 16.1706 |
| 14 days | 20 | 280 | 58 | 20.7143% | 14.0552 |
| 30 days | 13 | 390 | 38 | 9.7436% | 10.6120 |

Conditional MAE uses only filled dates and differs in sample composition. A lower long-gap conditional error is not evidence that long gaps are easy. The dashboard separately shows shared-date errors and coverage. The past-year median fills every masked date in these experiments but has substantially higher short-gap error; high coverage alone is not a reason to adopt it.

## Real missing-date proposals

No review-held value was replaced. The 67 absent training dates produce 67 recent-original proposals, 62 previous-week proposals, 67 weekday-median proposals and 67 past-year-median proposals. All are marked **unapproved feature-input candidates**. They are not inserted into the database, used as labels, or substituted into official exports.

Eligibility uses only past information: absent original and an available original within the previous three calendar days. It does not inspect a future gap endpoint. Recovery status remains unassessed; missing canonical data does not establish that an official PDF is absent or that a parser is at fault.

## Verification completed

| Check | Result |
| --- | --- |
| Synthetic treatment safeguards | 11 passed before real execution |
| New API/authentication/export tests | 4 passed |
| Full backend suite | 316 passed, 1 skipped |
| Ruff backend | Passed |
| Frontend suite | 46 passed |
| Frontend TypeScript | Passed |
| Next production build | Passed |
| Independent masked-trial reconstruction | All 4,450 matched |
| Conditional MAE/RMSE/bias recomputation | All 25 method/length summary rows matched |
| Export manifest verification | All 13 generated files matched hosted byte checksums |
| Drive archive receipts | All 14 archived outputs/manifest receipts matched |
| Independent Linux rerun | Study ID and every uncompressed CSV/JSON/Markdown exactly matched hosted Windows execution |
| Chart rendering | All 20 configurations: two charts × five lengths × two widths rendered SVG without NaN |
| Mobile chart visual review | Actual ECharts SVG rasterization inspected; horizontal labels remain readable |
| Production-build HTTP integration | Authenticated page and seven exports passed; CSV bytes match verified study files |
| Access controls | No-session export 401; invalid download 422; no-session page redirects to login |
| Data/model safety | 0 database writes, 0 fitted forecast models, 0 validation/test rows used |

One existing Starlette/httpx deprecation warning remains. The skipped test is the existing integration test, not a treatment failure. A full interactive browser preview was unavailable because the preview runner passes unsupported flags to Next; no full-browser acceptance claim is made. Charts were actually rendered through ECharts SSR, and page/auth/download behaviour was exercised over HTTP against the production build.

Python/platform gzip headers differ between Linux and Windows. Hosted compressed bytes match the hosted manifest; decompressed research outputs are byte-identical. Compression-container differences do not indicate changed study results.

## Evidence and reproduction

The protected page offers summary, all trial rows, mask windows, original training calendar, actual proposals, full JSON and Markdown report. Donor fingerprints hash the ordered original donor date/value/version/source tuples. Calendar and windows reproduce those tuples. All artificial masks in one length experiment are hidden simultaneously; estimates are never reused as donors.

Run on the exact archived input:

```text
python -m research.treatment_study --online
```

or:

```text
python -m research.treatment_study --bundle path/to/exact/frozen_input.zip --output data/treatment_study
```

Independently verify exported donor evidence, errors, manifests and receipts:

```text
python -m research.verify_treatment --folder data/treatment_study
```

The predefined protocol is in MISSING_TREATMENT_PROTOCOL.md. The workflow uses existing ignored Drive credentials, requires no DATABASE_URL, archives by checksum and leaves collection checkpoints unchanged.

## Next research decision

1. Investigate actual source recovery for missing/held dates where evidence is retained.
2. Pre-register a downstream input-treatment impact study: chronological folds, original-only target labels, common-date forecast errors, prediction coverage and donor provenance.
3. Assess recent-original treatment against the current input policy without using the already evaluated 2025 results to select a method.
4. Choose a valid subsequent confirmation period or collect prospective outcomes before claiming an improved model.

This delivery completes the treatment study, not the thesis. Broad historically unreported temperature/cost fields and long gaps are not authorized for automatic filling.
