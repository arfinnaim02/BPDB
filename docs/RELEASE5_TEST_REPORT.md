# Release 5 acceptance — 7 November 2026

## Delivered

Protected `/reports` dashboard and `/api/v1/research/report`: seven-page PDF, four vector SVG figures, twelve-row validation/test CSV, methods/results Markdown and complete JSON evidence. A report ID binds source identities, current data, first-issue prospective evidence and renderer source; generation time is excluded. Downloads reject a stale preview identity and refresh the preview instead of silently mixing snapshots.

Historical experiments remain frozen. No model refit, final-test reselection, target imputation, schema migration or canonical promotion occurs in this release.

## Checks completed

- Backend: **292 passed, 1 skipped** (opt-in PostgreSQL test); Ruff passed. Existing Starlette deprecation warning remains.
- Frontend: **31 passed**; TypeScript and Next production build passed.
- Authenticated server HTTP integration against the actual hosted report as a local fixture: report page plus all eight exports passed; PDF seven pages; CSV twelve rows; download hashes and report IDs match; stale preview refresh, unauthenticated 401 and invalid export 422 checks passed. This is HTTP integration, not production browser visual verification.
- Actual Windows-hosted Neon read/export: run https://github.com/arfinnaim02/BPDB/actions/runs/42344979821. Nine generated files preserved in its artifact (eight exports plus manifest). ZIP SHA256 `a099970791ed462b1543565b4d9bf72b5f2588a0bfdccad8e7f57b4438a8c42a`; every export byte count and SHA256 independently verified.
- Report ID: `747959a8ce0a0feba073c280dbbbfb89827c5e3bf348d5cd6f1729a31beb195a`. Seven PDF pages rendered and reviewed, including dense calibration/sensitivity, prospective and provenance pages; no clipping or pagination overflow observed.
- Live capture: **2,390 canonical dates**, 2019-10-19–2026-11-04; 184 calendar gaps between bounds. Gaps do not prove absent official reports.
- Prospective completed-target window 2026-08-09–2026-11-06: one attempted target, one earliest successful forecast, **zero scored dates**; MAE/RMSE/bias remain null. Three displayed attempts include tomorrow's issue and a retained reissue; these are not three independent scored targets.
- Historical finding unchanged: primary OLS MAE 15.500017136384958 million kWh versus lag-2 17.900679860627175 on 287 matched 2025 dates, a 13.41% reduction. Ridge practically tied; no universal superiority or verified live-accuracy claim.

## External blocker: Drive authorization

The hosted report was generated, but archival failed with Google `invalid_grant: Token has been expired or revoked`. **This workflow is correctly red, not accepted as a successful archive.** Its GitHub artifact still preserves the generated report for 30 days. Neither a verified Drive receipt nor a successful report archive is claimed. Existing Neon measurements remain intact. Future daily collection restoration/checkpointing also depends on valid Drive credentials.

To restore access on the original trusted computer containing `secrets/google_oauth_client.json`:

1. In the project root, rename the old ignored `secrets/google_drive_token.json` to an ignored backup within `secrets` (do not commit it). The current authorization script otherwise tries to refresh that revoked token.
2. Set `PYTHONPATH` to the project's `backend` directory, run the working virtual environment's Python with `-m ingestion.authorize_drive`, and complete Google consent using the same account and OAuth client.
3. Run `-m ingestion.setup_drive_storage`; require token refresh, upload, checksum and cleanup to pass. Preserve the existing Drive folder configuration.
4. Replace repository Actions secret `GOOGLE_DRIVE_TOKEN_JSON` with the entire new token JSON. Never put it in an issue, commit, browser-visible environment variable or chat. Keep the existing config secret unless the verified folder configuration changed.
5. Run **BPDB research reports** manually. Require archive verification and manifest/PDF verification to pass. Then run **BPDB daily collection** and require restore, processing, checkpoint and forecast steps to pass. Check the new report/collection logs, not an older green run.

The underlying token expiry/revocation cause is not proven by `invalid_grant`; review the Google OAuth app's publishing/access settings before relying on unattended long-term operation.

## Dashboard acceptance checklist

1. Sign in at https://bpdb-ng65.vercel.app/reports. Confirm the current report preview loads and its prospective sample count is visible.
2. Download PDF: seven pages, four figures, units, captions, dates and source identifiers. Download JSON and confirm its `report_id` matches the preview; capture both together.
3. Download model tables CSV: twelve rows, six methods in each of validation 2024 and final test 2025, numeric values, common sample counts. SVG downloads should open as vectors.
4. Confirm missing targets remain gaps in the chart, prospective unavailable scores show dashes, and historical MAE is not presented as prospective accuracy.
5. If data updates between preview and download, expect a refreshed preview banner and click download again.

## Next thesis work

Draft the literature review and full chapter narrative around retained methods/results, with real author/university requirements and supervisor review. Continue collecting prospective outcomes; the current zero-pair sample cannot support current-accuracy claims. Further model development needs a newly declared evaluation period rather than reusing 2025 as untouched data.

## Detailed-results expansion acceptance

- Expanded report: 18 pages, four existing vector figures, eleven detailed appendices. All six models have monthly matched MAE/RMSE/bias; validation and final-year common/own/coverage tables are explicit.
- Diagnostics are recalculated directly from the same 287 frozen common predictions. New tests compare reconstructed MAE with retained scores, check direction/win counts sum to sample size, sorted largest errors, quantile behavior and January empty common coverage.
- Checks: 293 backend passed, one skipped; 31 frontend passed; Ruff, TypeScript, production build and 13 authenticated HTTP checks passed. All 18 pages rendered; dense validation/error distribution pages inspected at full render size.
- User-facing PDF capture uses the actual Neon report generated 7 November 2026 at 12:00 Bangladesh; current canonical inventory and prospective evidence are that retained capture, not a claim of continuously refreshed file contents. The live Reports page generates new captures.
- Detailed capture report ID: `8545ec35dc721e713fd8dcfca3f6ed6d188d1928f5fd3de6a61d79e1764da25e`. Reports remain descriptive, retrospective where stated, and distinct from a complete submitted thesis.
- Drive token recovery remains required; this expansion does not claim that authorization was renewed.
