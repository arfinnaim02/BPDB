# Executed monthly production-cost experiment — 8 November 2026

## Result
The fixed monthly_cost_v1 protocol was executed against Neon in a read-only transaction. Execution succeeded; evidence is insufficient to select or claim an accurate learned monthly model. No database observations, canonical records, existing energy models or production policies were changed.

The target is the sum of reported national daily total production cost (BDT), not electricity market price or independently audited financial expenditure. The window is January 2025–October 2026: 22 calendar months, 10 complete eligible months and 12 excluded incomplete/held months. No missing monthly actual was filled or extrapolated.

## Historical prediction checking
| Method | Forecast months | Scored months | MAE (billion BDT) | RMSE (billion BDT) | MAPE |
|---|---:|---:|---:|---:|---:|
| Latest complete total | 13 | 8 | 7.8473 | 11.2448 | 17.00% |
| Latest daily mean × target days | 13 | 8 | 8.2825 | 11.3789 | 18.18% |
| OLS | 0 | 0 | Undefined | Undefined | Undefined |
| Ridge, fixed alpha=1 | 0 | 0 | Undefined | Undefined | Undefined |

OLS/Ridge required eight usable chronological training rows. No historical target had enough earlier rows under the registered availability and donor rules. Thus there are zero common scored months across all four methods. The observed baseline difference does not establish a learned-model winner. Retrospective forecasts use current canonical revisions; 305 daily publication timestamps in complete months are unknown. These are exploratory availability scenarios, not a reconstructed point-in-time operational trial.

## Frozen next-month predictions
Issued 8 November 2026 at 12:07:48 UTC (18:07:48 Bangladesh time), before the target month. Target: **December 2026**. October 2026 is the latest eligible donor. Eight historical fitting rows are now available.

| Method | December total production cost (BDT) | Status |
|---|---:|---|
| Latest total baseline | 86,248,509,438.00 | Baseline scenario |
| Daily-mean baseline | 86,248,509,438.00 | Baseline scenario; October and December both have 31 days |
| OLS | 66,581,275,459.36 | Unvalidated exploratory forecast |
| Ridge (predefined primary) | 65,062,154,697.58 | Unvalidated exploratory forecast |

Ridge is approximately BDT 6,506.22 crore (65.062 billion). Its primary designation was fixed before scores, not awarded for demonstrated superiority. These are point predictions without calibrated uncertainty intervals. December actual and prediction error remain undefined. Eight sparse training rows do not justify a dependable deployment claim.

## Verification completed
- Twelve focused tests passed on the hosted runner; local full backend suite: 357 passed, one existing skip.
- Artifact SHA256 and byte counts checked for all five manifested files.
- All complete monthly targets independently re-summed from exact decimal daily costs.
- Historical baseline MAE, RMSE, bias and MAPE independently recomputed.
- Future OLS/Ridge predictions independently reconstructed from retained coefficients and scaling parameters.
- Code and protocol hashes retained; database access was read-only.

## Files and reproduction
`monthly_audit.csv` lists every month and every missing/held date. `predictions.csv` includes historical predictions and actuals; empty actuals/errors are intentionally unscored. `future_forecast.json` freezes December predictions, fitting months and coefficients. `experiment.json` includes daily cost provenance, historical fold details and limitations. `verification.json` records numerical checks. `manifest.json` binds the original five outputs.

The full acquisition snapshot is preserved as `canonical_snapshot.json.gz.b64` to keep the evidence textual and compact. Decode with Python: `gzip.decompress(base64.b64decode(Path("canonical_snapshot.json.gz.b64").read_bytes()))`; compare decoded bytes with `manifest.json` before use. It contains public-report observations and source lineage, not database credentials.

Code/protocol commit: ee2293033682e1a2de4b2a708903683d26cd86df. Hosted execution: https://github.com/arfinnaim02/BPDB/actions/runs/42478712136 . Acquisition snapshot SHA256: 0fc2a3471a31217df6665860a2567669676db56777d3ade0da06c29d4d3d4b83.

## Next execution
1. Preserve these issued predictions unchanged. Do not tune using their future outcomes.
2. Investigate recoverable originals for the exact missing/held days in the monthly audit. Independently review reported cost definitions and anomalous values before calling this an accounting forecast.
3. After December finishes and all original daily costs pass the same eligibility rules, sum December actual cost and score each frozen forecast with signed error and absolute percentage error. If incomplete, mark unscorable; do not estimate the target.
4. Accumulate successive prospective monthly forecasts and outcomes. At least six shared scored months are the protocol's minimum for a tentative comparison, not proof of adequate statistical power or general reliability.
5. Keep the existing energy forecasts as a separate task. A future monthly energy experiment requires its own target, horizon and protocol. This cost study does not establish next-month energy accuracy.

Dashboard integration is not part of this commit. The frozen results are available in this evidence folder and the successful GitHub workflow; no claim is made that a new monthly dashboard has been deployed.
