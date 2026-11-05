# Release 2 — fixed model comparison protocol

Predeclared 5 November 2026 before the Release 2 results run. Release 1 and its results remain unchanged.

## Purpose and fixed input

Compare statistical autoregressive linear regression (OLS), Random Forest and Gradient Boosting with the two calendar-lag benchmarks and locked Ridge from Release 1. This bounded comparison tests model-family differences; it is not an exhaustive search or a final winning-model claim.

Use the exact Release 1 frozen archive, SHA-256 `bbcf319b97029d15a8180849b3f7ca218ef1e3ef7debf4ed01d32c511516c81a`, snapshot `7d45aacb7d94c05410e3ac9e97ceba3a7734500d4a1881e4829e2d7fab70acf0`. The hosted worker restores it by checksum from private Drive, not from a new Neon query. No database or collection-checkpoint writes occur.

Training 2020–2023, validation 2024, final test 2025 reserved. Original values, review holds and dense calendar gaps stay unchanged. Final-test labels are omitted from all modelling series and no test predictions/metrics are generated. Original raw input retains 2025 records for later evaluation.

## Timing and comparability

Same assumed retrospective timing as Release 1: issue noon Asia/Dhaka T-1; latest original input T-2. Known late records are refused. Unknown historical publication times are explicitly assumed; strict verified feature availability is reported separately. Current canonical revisions are not a point-in-time archive. No live-forecast-accuracy claim is supported.

All learned models use the same nine Release 1 features and its already training-selected exact-original-previous-week input substitution policy. Fixing the policy prevents a second search across imputations and isolates model-family effects. Donors are original past values only, never recursive. Labels and evaluation targets are never filled. OLS means an autoregressive regression with calendar terms, not an ARIMA/SARIMA fit.

## Predefined grid

| Family | Configurations |
| --- | --- |
| Autoregressive OLS | StandardScaler fitted inside each fold, then LinearRegression with intercept |
| Random Forest | 120 trees; max depth 4 or 8; minimum leaf 10; max features 1.0; bootstrap; one thread; seed 20261105 |
| Gradient Boosting | 150 trees; max depth 2 or 3; minimum leaf 10; learning rate 0.03; subsample 1.0; squared-error loss; seed 20261105 |

Five new configurations. No tuning after seeing 2024 results. There is no early stopping on validation or post hoc forecast clipping. Negative forecasts, if any, are counted.

## Selection and evaluation

Three expanding origins at 2021, 2022 and 2023, fixed fit once per full-year fold. Training labels stop at first target minus two days. Each candidate is scored on identical eligible dates with complete original Release 1 features. These exact folds and denominators must match Release 1's common-date training comparison (755 dates in its frozen execution). Fit can use the additional training rows permitted by the fixed substitution policy, exactly as the selected Release 1 Ridge did. Minimum 60 fit rows and 10 common fold dates remain execution floors, not proofs of statistical adequacy.

Within each new family, select lowest pooled training-fold MAE; break ties by configuration ID. Rank those three selected configurations alongside locked Ridge using training-fold MAE. The lowest is labelled **training-selected provisional finalist**, not a final thesis champion. Benchmarks remain evaluation references, not tuned models. All are compared in validation.

Refit each selected new model once through 2023-12-30, with train-only scaling, then keep parameters fixed throughout 2024. Freeze the selected settings and finalist before computing validation scores. Compare all six methods on identical observed 2024 target dates; report MAE, RMSE and signed bias plus own scored dates, calendar forecast coverage and negative-forecast counts. Recompute comparison denominators jointly; never place original 220-date Release 1 numbers beside scores from a smaller sample without disclosure. Monthly scores use the same common intersection. Report differences descriptively; no significance claim or test-year evaluation.

## Saved evidence and acceptance

Retain source hashes, protocol, runtime, folds, candidate scores, fitted coefficients/trees, 366 validation rows, result JSON, checksummed manifest and readable report in private Drive and a GitHub diagnostic artifact. Tree inference uses sklearn's float32 split-input semantics. Safe JSON saved-model predictions must agree with fitted sklearn predictions within 1e-8; no pickle is served or loaded by the website. Verify the locked Ridge matches Release 1 too. The authenticated website displays saved results and downloads; model fitting does not run in a request.

Tree impurity importance, when shown, describes fitted splits only. It is not causal and is not an unbiased ranking of feature usefulness. Prediction intervals, prospective availability capture and final-test evaluation are later work.

Primary implementation references:
- https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html
- https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html
- https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingRegressor.html
- https://scikit-learn.org/stable/common_pitfalls.html
