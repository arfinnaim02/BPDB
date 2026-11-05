# Release 3 — final evaluation and test report

Executed 5 November 2026. **The reserved 2025 period has now been evaluated under a protocol committed before its model scores were generated.** OLS remains the predefined primary model.

- [Original hosted final evaluation](https://github.com/arfinnaim02/BPDB/actions/runs/42010041257).
- Execution source commit: `ebe2d6a5bf63760efd0cfca31860abeb3121cce7`.
- [Final evaluation dashboard](https://bpdb-ng65.vercel.app/analytics/final-evaluation), after signing in.
- [Locked protocol](RELEASE3_PROTOCOL.md).

## What was completed

All four learned families were refitted once on eligible pre-2025 labels, with settings fixed from development. Every 2025 calendar date was evaluated using chronological past inputs. Final metrics, monthly comparisons, paired error sensitivity, safe saved models, source/code identities and downloadable thesis tables are delivered. The primary model was not switched after seeing test performance. No Neon data or collection checkpoint changed.

## Fit and sample

- Same original frozen 2020–2025 archive and snapshot as Releases 1 and 2; no fresh dataset selection.
- Nominal fit window 2020-01-01 through 2024-12-30. Actual usable fit rows: **1,557** for every learned model.
- Actual last usable fitting label: **2024-10-18**. The nominal cutoff is not a claim that every late-2024 date had a usable target and feature row; missing inputs/labels reduce the sample.
- Final year: **365 calendar days, 330 eligible observed targets, 35 missing targets**. No missing test target was filled.
- Primary OLS forecasts: **311/365 calendar days**; **303 observed targets scored** on its own available dates.
- Fair all-six-method comparison: **287 identical observed target dates**.
- Earlier 2025 originals may enter later test-year features at the T-2 cutoff. Model parameters never update on 2025 labels.

## Actual final-test results

Errors are in **million kWh**, with lower MAE/RMSE better. Bias is prediction minus observation. Display rounding does not alter saved precision.

| Method | Common dates | MAE | RMSE | Bias | Own scored | Forecasts /365 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Latest report · lag 2 | 287 | 17.9007 | 23.3982 | -0.1813 | 315 | 328 |
| Same weekday · lag 7 | 287 | 21.7705 | 28.4908 | 0.3013 | 313 | 327 |
| Ridge · refitted | 287 | 15.5000 | 19.7754 | -4.5088 | 303 | 311 |
| Autoregressive OLS · primary | 287 | 15.5000 | 19.7758 | -4.5085 | 303 | 311 |
| Random Forest | 287 | 19.2124 | 24.0754 | -12.5710 | 303 | 311 |
| Gradient Boosting | 287 | 20.2079 | 24.9544 | -14.4739 | 303 | 311 |

Primary OLS has **13.41% lower common-date MAE** than exact lag 2 in this historical test. Its mean absolute error is about 15.5 million kWh per scored day under the stated scenario. All methods produced zero negative forecasts.

Ridge is numerically lower by about **0.000020 million kWh MAE** and 0.000455 RMSE. This is a practical tie, not a reason to replace the predefined OLS primary model after testing. The tested tree configurations have higher MAE and stronger negative bias. No universal superiority, causal explanation or significance claim follows from this bounded comparison.

Own-date errors are also downloadable, but those methods use different dates. OLS own-date MAE is 15.7529 on 303 dates; the common-date table is the appropriate head-to-head comparison. Coverage is part of performance, not a detail to hide.

## Paired calendar-block sensitivity

Contrast: OLS absolute error minus lag-2 absolute error, on the same 287 common dates. Negative differences favor OLS. The three block lengths and 2,000 resamples each were specified before scoring. Unmatched/missing calendar rows travel with their blocks; circular resampling wraps at the year boundary.

| Block days | Common dates | Point MAE difference | 2.5th percentile | 97.5th percentile | Valid resamples |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 287 | -2.4007 | -3.8110 | -0.9040 | 2000 |
| 14 | 287 | -2.4007 | -3.7697 | -0.9046 | 2000 |
| 28 | 287 | -2.4007 | -3.8258 | -0.9918 | 2000 |

The descriptive ranges remain below zero for these three block lengths. They assess sensitivity to short-range dependence; they are **not daily prediction intervals, calibrated significance tests or a guarantee of future gains**. Wrap-around, seasonality, nonstationarity, one test year and missingness limit their interpretation.

## Executed software and numerical checks

| Check | Result |
| --- | --- |
| Full backend suite with research dependencies | **262 passed, 1 skipped** |
| New final-worker safety tests | **11 cases**: locked settings, dense calendar, train-only fitting, saved inference, origin cutoff, block sensitivity and retained-result reuse |
| New frozen-result API tests | **6 cases**, including protocol rejection even with a recomputed valid fingerprint |
| Frontend unit suite | **26 passed** |
| Backend Ruff | Passed |
| Frontend TypeScript | Passed |
| Frontend production build | Passed; final page and export route generated |
| Hosted final-year execution | Succeeded; result blobs and final-evaluation receipt retained in private Drive |
| Output integrity | Artifact digest and every manifest file size/SHA-256 independently verified |
| Final common-date scores | MAE/RMSE independently recomputed for all six methods from saved CSV, agreement within 1e-10 |
| Saved model inference | OLS/Ridge maximum difference 5.6843e-14; forest 2.2737e-13; boosting 4.5475e-13, all below 1e-8 |
| Code/protocol identity | Local worker key equals retained execution key |
| Test isolation | No 2025 labels fitted; no test parameter updates; donors no later than target minus two days |
| Database writes | Zero |

The skipped test is opt-in PostgreSQL integration; one existing Starlette/httpx deprecation warning remains. Ordinary lightweight CI can skip research-dependent tests, while the research environment executes them. An initial lightweight CI failure came from a test fixture importing worker-only Drive libraries; the fixture now mocks that boundary. No research algorithm, settings or retained result changed.

Authenticated local HTTP acceptance covers the default and May-filtered page, all seven exports, and refusal of an unauthenticated model export. This verifies server rendering and integration, not production-browser chart appearance.

## Once-only logical evaluation

The private Drive receipt binds this protocol/code key to checksummed output blobs. A subsequent hosted run with that key restores the retained result instead of fitting or rescoring. A different key is refused once the final evaluation exists. An identical-protocol retry after interruption before receipt retention is reproduction of the same logical evaluation, not a new model search. Offline verification is allowed; post-test tuning is not authorized by this report.

## Interpretation and thesis limits

Issue noon Bangladesh T-1, latest original input T-2. Historical publication times are unknown: **strict verified feature coverage is 0/365 test days**. The stated reporting-delay assumption and current canonical revisions prevent a verified point-in-time or live-accuracy claim. The original archive contained 2025 records before evaluation; this was a reserved model-evaluation period, not a blinded experiment.

Use the defensible thesis statement: “Under an explicitly assumed retrospective reporting-delay scenario, the predefined autoregressive OLS model reduced MAE relative to the latest-report benchmark on 287 matched observed days in 2025; Ridge performed practically equivalently.” Include coverage, errors, last usable fit label and limitations alongside that statement.

Do not describe 2025 as a new untouched test set in later tuned experiments. Additional development needs prospective evaluation or explicit exploratory labelling. Source correctness, historical revisions and missingness can still affect measurement validity. No source values were replaced by forecasts.

## Reproducibility identifiers

- Snapshot: `7d45aacb7d94c05410e3ac9e97ceba3a7734500d4a1881e4829e2d7fab70acf0`
- Final experiment: `0c68745e94929a3eb2feb27b6a94155b59d32a996070ef6602bc9d2ac08f12b6`
- Evaluation key: `b147ac22b2bf2b293aac8703bfb811e4eace0fda82e2ebe48079d69a72ccd938`
- Release 2 reference: `c22ee6e06c2e26c40ee4f1754c083760b3de585e03c70b59a95fa91457b8eac6`
- Artifact: `bpdb-release3-42010041257-1`.
- Artifact SHA-256: `9c5efda802344c211e4bad32264982647bd85e86b2f5669df104bccbb634c5b9`.

Private Drive retains frozen input, final features, predictions, safe model JSON, report and manifest. No pickle is used. GitHub diagnostic artifacts have 30-day retention. Reproduce the fixed protocol with `python -m research.release3 --bundle frozen_input.zip`, `PYTHONPATH=backend` and pinned research requirements. Different runtimes can change fingerprints; the hosted receipt restores the original result.

## Researcher acceptance checklist

1. Sign in and open **Final evaluation**. Confirm **2025 Evaluated**, primary OLS MAE about **15.5000**, **287** common dates and **311/365** primary forecasts.
2. Confirm the model card reports **1,557 fit rows**, cutoff **2024-12-30**, and actual last usable label **2024-10-18**.
3. Check the six-method metrics and three block-sensitivity rows against this report. OLS must remain the primary label despite the tiny Ridge advantage.
4. Toggle/zoom chart series and choose May in the exact-predictions table. Only May 2025 table dates should appear; annual scores stay fixed.
5. Download predictions: 365 data rows plus header, proper unit headings and blank missing targets. Download metrics (6 rows), monthly metrics (72 rows), sensitivity (3 rows), model JSON, full report JSON and execution report.
6. Confirm Releases 1/2 still show their historical development results, with links to the later final evaluation rather than implying the current test is still untouched.
7. Sign out and retry an export URL: access must be refused. No API key is entered into the browser.

## Next execution

The defined historical model-evaluation phase is now complete. Next, build a separately labelled daily research-forecast service with saved model/version lineage and prospective availability tracking, then assemble thesis methods/results and reproducible figures from these retained outputs. Do not promise operational reliability or silently refit the evaluated model. Any later deployment fit must receive a separate identity and must not overwrite this final-test evidence.
