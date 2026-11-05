# Release 2 — execution and test report

Executed 5 November 2026. **Hosted model comparison succeeded. The 2025 final test remains reserved.**

- [Successful hosted research run](https://github.com/arfinnaim02/BPDB/actions/runs/41991685905).
- Execution source: `0bbef0293e9c5e249eed3d4e84a3d54635939540`.
- [Authenticated Model comparison dashboard](https://bpdb-ng65.vercel.app/analytics/models).
- [Predeclared protocol](RELEASE2_PROTOCOL.md).

## Delivered work

Added autoregressive linear regression (OLS), Random Forest and Gradient Boosting to the locked Release 1 Ridge and two lag benchmarks. All learned models use the same nine features, original previous-week input policy and frozen study. Five new configurations were specified before execution. The worker restores the exact archived input from private Drive without a Neon query or database write. The website serves saved results; model training and live predictions do not run in web requests.

Training: 2020–2023. Validation: 2024. Final test: 2025 reserved. The 2024 calendar contains 366 days, 295 eligible observed targets and 71 missing targets. Missing labels and evaluation targets are never filled.

## Actual validation results

All methods below use **the same 220 observed 2024 dates**. Errors are in million kWh; figures are rounded here, with full precision in downloads. Bias is prediction minus observation.

| Method | Common dates | MAE | RMSE | Bias | Own scored dates | Forecasts /366 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Latest report · lag 2 | 220 | 19.2274 | 29.9165 | -0.0584 | 263 | 296 |
| Same weekday · lag 7 | 220 | 29.1578 | 41.5755 | -2.7487 | 255 | 295 |
| Locked Ridge | 220 | 18.1441 | 27.3086 | -3.5130 | 244 | 268 |
| Autoregressive OLS | 220 | 18.1426 | 27.3083 | -3.5117 | 244 | 268 |
| Random Forest | 220 | 22.0533 | 29.4687 | -10.9851 | 244 | 268 |
| Gradient Boosting | 220 | 22.9775 | 30.1601 | -13.3075 | 244 | 268 |

OLS and Ridge are practically tied in this comparison: their validation MAE difference is approximately **0.00146 million kWh**. This tiny descriptive difference is not evidence of meaningful or statistically significant superiority. Both outperform the tested tree configurations on common-date MAE. The tree models show more negative bias (underprediction on average); no causal explanation has been established. All six methods produced zero negative forecasts.

All learned methods forecast on 268/366 calendar days and can be scored on 244 dates individually; the all-method common intersection is 220. Own-date errors use different samples and are not a fair substitute for the common-date comparison.

## Training-only settings and provisional finalist

Each new family was selected within three expanding training origins (2021, 2022, 2023). These use exactly the same 755 common scoring dates as Release 1. No configuration or policy was changed after validation was scored.

| Family | Selected configuration | Training-fold MAE | Training-fold RMSE |
| --- | --- | ---: | ---: |
| Autoregressive OLS | ols | 12.6678 | 17.9042 |
| Locked Ridge | release1_locked_ridge | 12.6693 | 17.9055 |
| Random Forest | rf_depth_8 | 15.5772 | 20.2117 |
| Gradient Boosting | gb_depth_2 | 15.6438 | 20.2919 |

The **training-selected provisional finalist is OLS**, fixed before validation scoring. Locked Ridge remains the close reference. Random Forest selected depth 8; Gradient Boosting selected depth 2. Each new final model used 1,313 fit rows with the last usable label on 2023-12-25, cutoff 2023-12-30; parameters remain fixed throughout 2024. The shortlist is not a final-test result or operational model certification.

OLS here is a statistical autoregressive linear regression with calendar terms, not ARIMA/SARIMA. Holding the Release 1 features and input policy fixed isolates model-family effects; this bounded experiment does not establish that every possible tree configuration is inferior.

## Executed software and numerical checks

| Check | Result |
| --- | --- |
| Full backend suite with research dependencies | **245 passed, 1 skipped** |
| New worker safety/serialization tests | **8 passed**, including training-only selection and float32 tree splits |
| New result API tests against hosted assets | **4 passed** |
| Frontend unit suite | **23 passed** |
| Backend Ruff | Passed |
| Frontend TypeScript | Passed |
| Frontend production build | Passed; comparison page and export proxy generated |
| Hosted research execution | Succeeded; frozen input restored and outputs verified in private Drive |
| Result manifest | Every listed file byte length and SHA-256 independently verified |
| Saved validation scores | All six common-date MAE/RMSE values independently recomputed from saved CSV, within 1e-10 |
| Saved-model inference | OLS 5.6843e-14; forest 2.8422e-13; boosting 3.4106e-13 maximum difference, all below 1e-8 |
| Locked Ridge reproduction | Maximum difference 5.6843e-14 |
| Calendar and test isolation | 366 validation rows; no 2025 predictions or scores; no test labels in modelling series |
| Database writes | Zero |

The skipped test is the opt-in PostgreSQL integration test. One existing Starlette/httpx deprecation warning remains. Ordinary CI without research packages may skip sklearn-dependent tests; the research worker installs those packages and executes its safety tests. Unit tests use synthetic data; the model scores above come from the real frozen BPDB dataset.

Local authenticated HTTP acceptance checks covered the default page, May filter, all five downloads and refusal of an unauthenticated model export. This checks server rendering and integration, not visual chart appearance in the production browser.

## Scientific limits

Forecast issue is noon Bangladesh T-1 with latest original input T-2. Historical publication times are unknown. **Strict verified publication-time feature coverage is 0/366 validation days.** Known late values are refused, while unknown times are accepted only within the stated retrospective reporting-delay assumption. These results use current canonical revisions and do not establish point-in-time or live forecasting accuracy.

The validation period has already been explored. No 2025 final-test result, prediction interval, significance test or causal conclusion is reported. Tree impurity importance is descriptive and potentially biased. Forecasts never replace original observations.

## Identifiers and retained evidence

- Snapshot: `7d45aacb7d94c05410e3ac9e97ceba3a7734500d4a1881e4829e2d7fab70acf0`
- Release 2 experiment: `c22ee6e06c2e26c40ee4f1754c083760b3de585e03c70b59a95fa91457b8eac6`
- Release 1 reference: `fb42fc543c5b412475ad085dd14a028da3629e0e6085172e20945118f50ad76c`
- Artifact: `bpdb-release2-41991685905-1`.
- Artifact SHA-256: `07451db6c6ab84acd4cf31a2acbd3ff69087e0be93fa4dbe617785460286492a`.

Private Drive retains frozen input, model coefficients/trees, predictions, training selection, reports and checksummed manifests. The model JSON is safe data; no pickle is loaded by the website. GitHub diagnostic artifacts have 30-day retention. Reproduce with `python -m research.release2 --bundle frozen_input.zip`, `PYTHONPATH=backend` and pinned research requirements. Runtime differences can change the experiment fingerprint.

## Researcher dashboard acceptance checklist

1. Sign in and open **Model comparison** in the sidebar. Confirm six methods, 220 common validation dates, OLS as training-selected provisional finalist and **2025 Reserved**.
2. Check the six MAE/RMSE rows against this report. Confirm the publication-time warning and coverage columns are visible.
3. Toggle chart legend entries and zoom. OLS/Ridge can overlap; missing actual values must remain gaps.
4. Select May in the prediction table. Only May 2024 dates should appear; scores and chart remain the full 2024 comparison.
5. Download predictions: one header plus 366 rows; units in headings, numeric values, blank missing observations and no 2025 forecasts.
6. Download training selection (five candidate rows), saved models JSON (four learned models), full comparison JSON and execution report. Confirm the experiment ID above and null reserved-test metrics/predictions.
7. Sign out and reopen an export URL. It must refuse access. API keys remain on the server.

## Next release

Freeze the final evaluation protocol and candidate choice, then evaluate 2025 once under the same disclosed timing scenario. OLS is the predefined primary finalist from training; Ridge and the two lag benchmarks provide reference comparisons. Refitting choices, evaluation coverage and any uncertainty analysis must be fixed before viewing final-test scores. Then integrate the evaluated model into the research dashboard and write the thesis methodology/results around retained evidence. Prospective operational forecasting additionally needs reliable publication/availability tracking.
