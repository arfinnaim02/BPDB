# Release 5 - research evidence reports and vector figures

The report generator reads verified frozen Releases 1-3 and a repeatable-read, read-only Neon snapshot of current inventory and prospective forecast records. It does not fit models, rerun final-year selection/evaluation or update source/forecast tables.

## Outputs

- A seven-page A4 PDF: study summary; chronological methods and coverage; validation/test comparison; final-year time series and monthly errors; matched-date calibration and paired sensitivity; prospective monitoring; provenance and limitations.
- Four standalone vector SVG figures: model MAE comparison, observed-versus-OLS 2025 series, monthly OLS/lag-2 MAE and matched-date observed/predicted scatter.
- A clean 12-row model-comparison CSV, methods/results evidence Markdown and full report JSON.
- A checksummed file manifest and verified private Drive archive from the hosted export workflow.

The report is evidence supporting thesis writing, not a complete submitted thesis or an invented institution/author template. The user must still complete the literature review, university formatting and academic review.

## Data identity and numerical interpretation

The stable report ID binds frozen source IDs, report code hashes, current inventory, actual issue/outcome records and prospective summary evidence. Generation time alone is excluded. The ID is not a PDF-byte checksum; exported content hashes and hosted manifests identify specific file bytes.

A download must match the preview's expected report ID. Changed live records or a changed reporting window require refreshing the preview rather than silently exporting different numbers. All files in a hosted export are generated from one captured report object.

Frozen 2024 validation and 2025 test scores use different matched samples and differently refitted models. They are displayed side by side descriptively, never as a paired year-to-year comparison. OLS remains the predefined primary model despite practical equivalence to Ridge. Historical reporting-time assumptions and 0/365 strict verified historical feature days remain explicit.

Plots retain dense calendar spacing and missing-value gaps. Bars start at zero. Calibration scatter uses the same 287 all-method common dates and equal scales on both axes. Its diagonal is a reference, not a fitted calibration line. Circular-block ranges remain descriptive dependence sensitivity, not forecast intervals or calibrated significance tests.

Current inventory is separate from the frozen 2020-2025 modelling sample. Prospective errors are separate from historical test errors. Pending actuals remain blank, empty error metrics remain unavailable and small samples do not establish reliability.

The prospective summary includes all first-successful-issue/actual pairs in its 90-day window, even when those issues fall outside the displayed history limit. Attempted target dates and summary evidence are retained in report JSON and checked against the reported counts/error values.

## Automation and access

The new report workflow runs manually, on its own setup push, and after successful main-branch daily collection. It checks out trusted main, shares the existing pipeline concurrency group, uses existing Neon/Drive secrets and captures the database through a read-only transaction. It archives new content-addressed report blobs and an indexed receipt without replacing collection checkpoints or historical evaluation receipts.

The website uses existing authentication and server-only API credentials. Exports are bounded and allowlisted; no arbitrary file path or model-fitting endpoint is exposed. ReportLab 4.4.9 renders vector PDFs/SVGs without a training dependency or external image service.

Acceptance includes real hosted database capture/archive verification, manifest byte/SHA-256 checks, seven-page PDF verification, visual inspection of rendered pages, SVG XML/provenance checks, preview/download consistency, authentication, TypeScript/build and relevant regression tests.
