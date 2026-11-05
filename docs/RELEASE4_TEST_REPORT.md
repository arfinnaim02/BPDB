# Release 4 — prospective research forecasts and test report

Executed 5 November 2026. **Saved-model inference is connected to Neon and the daily collection workflow.** Research predictions remain separate from authoritative BPDB measurements.

- [Successful hosted setup and acceptance run](https://github.com/arfinnaim02/BPDB/actions/runs/42029081589).
- Execution source: `3cd83cd34337c7bb809a0044d07601c59fc77c97`.
- [Research forecasts dashboard](https://bpdb-ng65.vercel.app/forecasts), after signing in.
- [Operating protocol](RELEASE4_PROTOCOL.md).

## First real retained issue

| Field | Retained value |
| --- | --- |
| Target operational date | **2026-11-06** |
| Actual issue time | **2026-11-05 18:41:00.799804 Asia/Dhaka** |
| UTC issue time | `2026-11-05T12:41:00.799804+00:00` |
| Status | Forecast |
| Predicted national energy | **320.957156601 million kWh** |
| Latest original donor actually used | **2026-11-03** |
| Substituted past-input slots | **1 of 9** |
| Input slots with unknown official publication time | **9** |
| Retained actual/error at execution | Not yet available; blank, not zero |
| Prospective scored dates at execution | **0** |
| Issue ID | `75272ea258e47500c75e7124b181437d019ac2dc8c78ff4dd5ceaa867f637fcb` |
| Saved model ID | `04aac742dbd25a35070b86e12279e51a3e762099696399221cb8a23244a8a2f3` |
| Historical final experiment | `0c68745e94929a3eb2feb27b6a94155b59d32a996070ef6602bc9d2ac08f12b6` |

One required input used the prescribed exact-original-previous-week donor. The newest used original was 3 November, so this is not a claim that every 4 November input was present. Substitution affects only past model features; no missing target or original observation was filled.

The actual issue time is retained rather than backdated to the planned noon schedule. These are prospective research records of platform-available inputs, not independent verification of unknown official publication times or a guarantee of operational accuracy.

## What changed

- Alembic **0003_research_forecasts** adds two separate tables: immutable forecast attempts and versioned later-actual comparisons. The hosted PostgreSQL upgrade and Alembic schema check passed.
- The saved Release 3 OLS model is used directly, with its exact scaler/coefficients and hash identity. No training or model selection runs in a web request or daily issue step.
- The daily workflow issues the next Bangladesh day's forecast after successful collection and verified Drive state. It applies migrations before the forecast step and reports forecast infrastructure errors. Successfully recording a withheld attempt is a valid execution, not a fabricated prediction.
- Captured source/version identifiers, checksums, original values, eligibility reasons, chosen donors, feature values and linear contributions are retained in the forecast payload.
- An identical model/target/input fingerprint reuses the first issue and timestamp. Changed input snapshots create distinct records; earlier predictions are never overwritten.
- Later canonical outcomes are compared only after the target day ends, with each actual revision retained separately. Automatic reconciliation covers the last 90 completed target days, with a disclosed safety cap.
- Prospective summaries use the earliest successful forecast per target and its latest retained actual revision. They do not select a later forecast for a better error.
- Added authenticated read-only history/detail APIs, a daily research dashboard, observed-versus-predicted chart, input evidence/model arithmetic and CSV/JSON exports. New Neon records appear without a frontend redeployment.
- Added desktop sidebar scrolling so the expanded navigation remains reachable; mobile horizontal navigation remains unchanged.

## Executed checks

| Check | Result |
| --- | --- |
| Full backend suite with research dependencies | **279 passed, 1 skipped** |
| Focused forecast/API/migration/readiness checks | **23 passed** |
| Frontend unit suite | **29 passed** |
| Backend Ruff | Passed |
| Frontend TypeScript | Passed |
| Frontend production build | Passed; forecast page and export proxy generated |
| Real Neon migration and schema comparison | Passed |
| Identical hosted rerun | Same issue ID and original timestamp; second insert refused as duplicate |
| Original source tables | Row counts unchanged across migration/issuance; new code inserts only into forecast/outcome tables |
| Artifact integrity | Artifact digest and hosted report checksum independently verified |
| Live saved-model arithmetic | Independently recomputed **320.957156600774**, agreeing with stored nine-decimal value within 1e-8 |
| Source-date/capture evidence | Donors no later than T-2; known source/version timestamps no later than capture; capture before actual issue |
| Feature construction | Independently rebuilt from retained original-donor values and calendar terms |
| Withholding, unsafe values and future timestamps | Tested without inventing outputs |
| Outcome revisions and earliest-issue scoring | Tested with separate retained revisions; repeated outcome insert deduplicated |
| Authentication and numerical exports | Tested; pending actual/error remains blank |

Local authenticated HTTP acceptance used the real hosted issue as a frozen SQLite fixture. It covered the default/selected-issue page, history CSV, issue JSON and unauthenticated export refusal. This is a server-rendering/integration check, not a claim of production-browser visual acceptance. The real Neon migration, capture, issuance and idempotency were checked in the hosted run separately.

The skipped backend test is opt-in PostgreSQL integration; the real hosted PostgreSQL migration/inference check passed. One existing Starlette/httpx deprecation warning remains. Research-dependent tests can be skipped in ordinary lightweight CI; the full local research environment executes them.

Source-table count equality is an operational check, not an independent checksum proof of every original value or PDF. Existing canonical tables are read, not updated, by the new inference service.

## Model and interpretation

The model remains the exact historically evaluated OLS fit: **1,557 usable rows**, last usable fitting label **2024-10-18**. It is not silently refitted using 2025 or newer data. Historical 2025 common-date MAE was about **15.5000 million kWh** under the explicitly assumed retrospective reporting-delay scenario. That number is separate from the new prospective log, whose scored-date count is initially zero.

Actual inference uses original dates through T-2 and records the real platform capture before actual issuance. Known future creation/retrieval/publication/availability timestamps are excluded; unknown official timestamps remain visible. Model age, shifts in conditions, measurement quality and input substitution can affect future errors. No future prediction interval or current accuracy guarantee is invented.

A withheld issue has a null prediction with an explicit reason. Pending actuals/errors stay null. New canonical revisions never silently change an already issued prediction. The 90-day summary reports attempted/forecast/scored target counts so missing outcomes are not hidden behind a single error metric.

## Operational sequence

1. GitHub's existing daily collection workflow runs on its noon Bangladesh schedule; exact execution can be delayed.
2. After collection and verified Drive checkpoint succeed, apply pending schema migrations and run `python -m ingestion.issue_forecast --apply` with `PYTHONPATH=backend`.
3. Capture bounded canonical inputs, issue or withhold tomorrow's research forecast, and retain recent eligible outcome comparisons.
4. The web dashboard reads current forecast rows from Neon. No redeployment is needed for each new issue.

Read-only database preview: `python -m ingestion.issue_forecast` without `--apply`. A preview is not an issued forecast. The separate setup workflow can also be manually run; identical inputs reuse the original retained issue.

## Researcher acceptance checklist

1. Open **Research forecasts**. Find the first retained 6 November issue above; expect about **320.9572 million kWh** and its actual Bangladesh issue time.
2. Before the target outcome arrives, observed actual, absolute error and prospective MAE must remain blank/undefined. Zero scored dates must not be shown as zero error.
3. Inspect the issue: expect nine past-input slots, one prescribed substitution, latest used donor 3 November, source PDF links, version/checksum evidence and saved linear arithmetic.
4. Download displayed-history CSV and this issue's JSON. Confirm the issue/model IDs match above and missing actual/error cells are blank.
5. Check the model card distinguishes historical 2025 MAE from prospective scores and shows the actual 2024 last-fit label.
6. After a later successful collection supplies an eligible completed-day actual, the outcome should appear with its version and comparison time. No prior forecast value should change.
7. Sign out and retry the export URLs: access must be refused. No API key is entered into the browser.

## Evidence identifiers

- Artifact: `bpdb-forecast-setup-42029081589`.
- Artifact SHA-256: `bcd7728b443a2139001f9836648e478bf788b807d5d8519e110e128d5109d2af`.
- Forecast and model IDs are listed above; complete source snapshots are retained in Neon issue payloads.
- Historical Releases 1–3 and their frozen results remain unchanged.

## Next execution

Build thesis-ready figures and an automated research report from the retained historical evaluation plus the separately labelled prospective log. Draft methods/results and limitations from actual outputs. Let prospective outcomes accumulate before claiming current operational accuracy. Any later deployment refit needs a distinct model identity and must preserve the existing final-test evidence.
