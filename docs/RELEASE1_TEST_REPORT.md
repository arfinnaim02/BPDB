# Release 1 — execution and acceptance report

Executed 5 November 2026. **Result: the historical experiment ran successfully; final 2025 testing remains reserved.**

- Hosted execution: [successful research run 41983140391](https://github.com/arfinnaim02/BPDB/actions/runs/41983140391).
- Source commit for that execution: `4354e813c03e640bb48b9f8722c284ce7fe92a2d`.
- Dashboard: [Forecast experiments](https://bpdb-ng65.vercel.app/analytics/experiments), after signing in.
- Protocol: [RELEASE1_PROTOCOL.md](RELEASE1_PROTOCOL.md).

## What was delivered

A frozen national energy-generation study, two calendar-lag benchmarks, a trained Ridge model, training-only missing-input comparisons, validation predictions, model/scaler JSON, checksummed evidence, and an authenticated results dashboard with downloads. Original measurements, calendar gaps and Neon records were not overwritten. The website serves saved research results; it does not train during a page request or produce live forecasts.

## Study sample

Target: national daily energy generated, **million kWh**. Every calendar date is retained.

| Year | Role | Calendar days | Observed targets | Eligible targets | Held targets |
| --- | --- | ---: | ---: | ---: | ---: |
| 2020 | Training | 366 | 348 | 333 | 15 |
| 2021 | Training | 365 | 349 | 348 | 1 |
| 2022 | Training | 365 | 354 | 354 | 0 |
| 2023 | Training | 365 | 343 | 343 | 0 |
| 2024 | Validation | 366 | 295 | 295 | 0 |
| 2025 | Reserved final test | 365 | 330 | 330 | 0 |

Held values remain in the original snapshot but are excluded from model labels. Missing labels and validation targets are never estimated. Input availability reduces usable model rows further.

## Actual validation results

All three models are compared on **the same 220 observed 2024 dates**. Errors are in million kWh. Bias is prediction minus observation. Displayed figures are rounded; downloaded files retain numerical precision.

| Model | Common dates | MAE | RMSE | Bias | Own scored dates | Calendar forecasts /366 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Latest report, exact lag 2 | 220 | 19.2274 | 29.9165 | -0.0584 | 263 | 296 |
| Same weekday, exact lag 7 | 220 | 29.1578 | 41.5755 | -2.7487 | 255 | 295 |
| Ridge | 220 | 18.1441 | 27.3086 | -3.5130 | 244 | 268 |

Ridge has about **5.63% lower MAE** than lag 2 on these common dates. This is a descriptive validation improvement, not a statistical-significance claim or a final winning-model conclusion. Ridge has lower calendar forecast coverage than either benchmark. Own-date scores use different date sets and must not be used as a fair head-to-head comparison.

Training-only selection compared 12 policy/alpha combinations across three expanding full-year origins (2021, 2022, 2023), on 755 common scored dates. Selected configuration: **exact original previous-week input substitution; Ridge alpha 0.1**. Pooled training-fold MAE: 12.6693. Final fit: **1,313 rows**, with last usable label 2023-12-25 and cutoff 2023-12-30. Scaling was fitted within training folds. Validation results did not select the configuration.

The initial execution refused a first fold containing only 49 complete rows under a complete 28-day rolling mean. Before model comparisons were produced, that rolling feature was removed; exact lag 28 was retained. The 60-row execution floor was not lowered. The successful run uses the documented nine-feature protocol.

## Missing-input experiment

Training originals were artificially hidden using seed 20261105, with 20 separate blocks per length. Only original past donors were permitted. These results describe reconstruction under artificial masks, not the real missingness mechanism.

| Hidden block | Previous original within 3 days: filled /masked | Conditional MAE | Exact original previous week: filled /masked | Conditional MAE |
| --- | ---: | ---: | ---: | ---: |
| 1 day | 20/20 | 9.9794 | 19/20 | 11.8202 |
| 3 days | 59/60 | 14.8790 | 58/60 | 21.2838 |
| 7 days | 59/140 | 14.9200 | 134/140 | 20.4404 |

Observed-only fills zero values and has undefined reconstruction error, not zero error. Conditional errors depend on which dates a policy can fill. The dashboard and JSON also report common filled-date errors. Missing-input reconstruction did not fill any validation or test targets; forecast-policy selection used training-fold forecast error.

## Executed software and numerical checks

| Check | Result |
| --- | --- |
| Full backend suite with research dependencies | **233 passed, 1 skipped** |
| Backend Ruff | Passed |
| Python compilation of changed research/API code | Passed |
| Frontend unit suite | **20 passed** |
| Frontend TypeScript | Passed |
| Frontend production build | Passed; experiments page and export route generated |
| Research worker hosted execution | Succeeded, including private Drive result archival |
| Frozen output manifest | All listed SHA-256 checksums and byte lengths independently verified |
| Saved validation scores | Independently recomputed MAE/RMSE from saved predictions; agreement within 1e-10 |
| Saved model inference | Maximum difference 5.684341886080802e-14, below 1e-8 tolerance |
| Test isolation | No 2025 labels in modelling series, no 2025 predictions/scores or feature-export rows |
| Database writes | Zero |

The skipped backend test is the opt-in PostgreSQL integration test. The suite reports one existing Starlette/httpx deprecation warning. Research packages are worker-only dependencies; ordinary CI can skip research-dependent tests when those packages are absent. Passing tests establish implemented behavior, not independent verification of every original PDF measurement.

## Important interpretation limit

Issue time is noon Bangladesh on T-1 for target T. An original day D report is assumed available at noon D+1, so the latest input is T-2. Historical publication times are unknown in this sample. **Strict verified publication-time feature coverage is 0/366 validation days.** Known late inputs are refused, but unknown times are assumed only within this labelled retrospective scenario. Results use current canonical revisions and do not establish point-in-time or live forecast accuracy. The 2024 period has previously been explored descriptively. The raw frozen input retains 2025 originals for later evaluation; reservation is not encryption or a claim that those data have never been seen.

## Reproducibility identifiers

- Snapshot: `7d45aacb7d94c05410e3ac9e97ceba3a7734500d4a1881e4829e2d7fab70acf0`
- Experiment: `fb42fc543c5b412475ad085dd14a028da3629e0e6085172e20945118f50ad76c`
- GitHub artifact: `bpdb-release1-41983140391-1`
- Artifact SHA-256: `ce897a666e99d195e9f44f703607905ca8afc801fa7fc7279da9dd06f57de542`

Frozen input, features, predictions, selection table, model, report and manifest were retained privately in Drive. GitHub diagnostic artifacts expire according to workflow retention. Offline reproduction uses `python -m research.release1 --bundle frozen_input.zip` with `PYTHONPATH=backend` and the pinned research requirements. Different runtime versions may produce a different experiment fingerprint.

## Dashboard acceptance tests for the researcher

1. Sign in and open **Forecast experiments** in the sidebar. Expect 1,313 training rows, 220 common validation dates and **2025 Reserved**. Confirm the publication-time warning is visible.
2. Check the comparison table against the three validation rows above. Toggle chart series and zoom. Missing observations must remain gaps, not zero values.
3. Change the exact-predictions month to May. The table must contain May 2024 dates only; the overall comparison must still use 220 dates.
4. Download **Validation predictions CSV**. Expect one header plus 366 calendar rows for 2024, units in headings, numeric prediction columns and blank missing values. There must be no 2025 predictions.
5. Download **Training selection CSV**, **Saved model JSON**, **Full experiment JSON** and **Execution & test report**. Confirm all download; the JSON experiment ID must match above, and reserved-test metrics/predictions must be null.
6. Sign out. Export URLs must refuse access without a session. No API key should be entered into the browser or CSV.

Automated tests and local integration checks do not substitute for the researcher's final production-browser acceptance of chart appearance and downloads.

## Next execution

Release 2 should add a small predefined statistical/tree-model comparison under the same timing assumption, study split and common-date evaluation. Select configurations within training, compare validation errors and coverage, then freeze the final shortlist before a separately authorized one-time 2025 evaluation. Only after that evaluation should the thesis describe the final selected model. A live forecasting capability additionally requires reliable prospective publication/availability tracking.
