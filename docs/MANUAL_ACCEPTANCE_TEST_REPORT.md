# Executed manual-checklist acceptance report

Date: **8 November 2026, Bangladesh**. Real-data capture: 2026-11-08T17:05:17.182106+06:00.

**Outcome: all executed automated, real-backend, export-integrity and component/HTTP checks passed. A full signed-in production-browser walkthrough was not completed.**

Application under test: [334f7f40](https://github.com/arfinnaim02/BPDB/commit/334f7f4005117d3d410a6543d0411b6fa79d5f8e). Local copies were verified against all 206 tracked application Python/frontend source files. Test-only harness commit: [b427ad9e](https://github.com/arfinnaim02/BPDB/commit/b427ad9e60d62cb7566e48cd29ea90e10aa02069). No application behaviour, official measurement, frozen result or production model was changed.

## Test layers

| Layer | Executed result | Scope |
| --- | --- | --- |
| Full local backend | **345 passed, 1 skipped** | Includes two new export-integrity harness tests |
| Full frontend | **48 passed, 0 failed** | Existing application tests and chart rendering |
| Ruff | Passed | Current backend sources |
| TypeScript | Passed | Current frontend sources |
| Production build | Passed | Current Next routes, including strategy/preparation |
| Live backend acceptance | Passed | Current FastAPI code against live Neon, read-only sessions, ephemeral test authentication |
| Actual React controls | **9 scenarios passed** | Rendered real component in jsdom 31.0.0 and dispatched change events |
| Frontend HTTP integration | **9 scenarios passed** | Production build with captured, verified real API/bundle responses |
| Live browser access protection | Passed | Protected production URL visibly redirected to login |
| Signed-in production browser click-through | **Not run** | Browser has no authenticated session; no password requested in chat, entered or changed |

The live backend run is [42474108903](https://github.com/arfinnaim02/BPDB/actions/runs/42474108903), successful. Foundation checks, backend CI and both Vercel status checks for the harness commit also succeeded. Hosted CI can skip optional-learner tests when research packages are not installed; the full local count above uses the available research dependencies.

## Results mapped to the ten manual checks

| Manual check | Result and evidence |
| --- | --- |
| 1. Strategy page opens | Authenticated production-build HTTP render passed; actual production browser correctly requires login |
| 2. Two profiles | Live backend + HTTP render: long-history core and modern reporting; joint eligible dates remain unapproved/null |
| 3. Variable coverage | Live read-only assessment returned 13 variables; rendered captured real counts without sample substitution |
| 4. Question-to-profile mapping | Rendered page includes the mapping and additional-data requirement for zonal forecasting |
| 5. Modern-variable filling safeguard | All eight modern-field API bypasses returned 422 with the intended guard reason; disabled option verified |
| 6. Core → modern → core switching | Actual React component reset to observed-only for every modern field; returning to core re-enabled choice without auto-selecting treatment |
| 7. Observed-only preview | Real gas February window returned 14/7/7 calendar days, no estimated rows |
| 8. Downloaded bundle | Three real exports downloaded; 12 declared payload-file checksums verified; blanks, original decimals, zeros and holdout treatment retained |
| 9. Existing pages | Automated regressions and full route build passed; full signed-in production page walkthrough remains unverified |
| 10. Login protection | Live browser redirected protected route to /login; API no-key requests returned 401; frontend exports without a session returned 401 |

## Real export findings — missing data is not a software failure

| Export case | Calendar rows | Missing original cells | Original zero cells | Estimated rows |
| --- | ---: | ---: | ---: | ---: |
| Gas supplied, February 2025 | 28 | 4 | 0 | 0 |
| Energy generated, January 2025 | 31 | 23 | 0 | 0 |
| Energy unserved, February 2025 | 28 | 4 | 1 | 0 |

February gas and unserved missing dates: **1, 5, 8 and 11 February 2025**. January energy had **23 blank originals**: 1–22 January and 29 January. The exported values stayed blank; they were not turned into zero, a forecast or an estimate.

The energy-unserved export retained one real numerical zero. Incomplete monthly observed totals stayed blank. These software-test windows do not establish an adequate scientific training sample or a complete reporting period.

Gas February split accounting:

| Split | Calendar days | Observed target candidates | Missing days | Estimated days |
| --- | ---: | ---: | ---: | ---: |
| Training | 14 | 10 | 4 | 0 |
| Validation | 7 | 7 | 0 | 0 |
| Test | 7 | 7 | 0 | 0 |

These three live windows contained no review-held rows. Hold preservation was covered by the existing synthetic/unit tests, not falsely claimed as a real held-row example in these exports.

## Negative and integrity checks

- Missing API key: 401; no data returned.
- Experimental previous-week treatment for all eight modern-only fields: 422, with the intended guard detail.
- Impossible date, reversed cutoffs, unknown metric and unknown policy: 422.
- Stale snapshot fingerprint: 409; no stale bundle served.
- Frontend download without a preview identity: 422 before upstream fetch.
- Download byte equality: local production-build proxy returned the exact verified hosted ZIP bytes for all three cases.
- Export headers: application/zip, attachment disposition, no-store and nosniff.
- CSV: proper headings, chronological unique dates, finite original numerical strings, no invented missing values, no prepared validation/test targets.
- Bundle: exact five members including manifest; every declared payload size and SHA-256 matched. An intentionally modified CSV was rejected by the acceptance checker.
- API outage simulation: explicit error panel, no cached/sample coverage assessment substituted.
- UI controls: modern-field treatment disabled in server-rendered HTML and in the actual React state-change tests.

## Boundaries of this result

The production cloud browser had no signed-in session. It visibly reached the legitimate workspace password screen; this was not a bot block. No credential was read, guessed, reset or changed. Consequently, this report does not mark a full authenticated production-browser or mobile visual walkthrough as passed.

Frontend HTTP replay used the exported real API payloads and ZIP bytes as local fixtures. It tests the current production-build rendering/proxy/error paths, while the independent hosted backend run tests actual Neon reads and exports. React component interaction used a DOM test environment, not a real browser.

The existing Starlette/httpx deprecation warning and existing skipped integration test remain. No new application defect was found in the executed paths. Source-retrieval failures and incomplete historical observations reported in earlier investigations remain separate unresolved data-quality work.

## Reproduction and retained evidence

Run **BPDB manual-check read-only acceptance** in GitHub Actions, or with the existing DATABASE_URL configured:

```text
python -m research.check_manual_acceptance
```

The script checks PostgreSQL read-only mode, uses temporary authentication solely in its ephemeral test application, and writes diagnostic previews, real research bundles and verification JSON under data/manual_acceptance. It does not change production credentials or publish a training result. The workflow retains its artifacts for 30 days.

[Machine-readable verification](MANUAL_ACCEPTANCE_VERIFICATION.json) records source commits, snapshot identities, test layers and explicit limitations.

## Decision

The executed software checks pass. Continue with source recovery and question-specific dataset eligibility work. Do not interpret passing software tests as missing-data resolution, model readiness or improved forecasting accuracy.
