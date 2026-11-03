# Canonical-gap recovery investigation

Implemented 3 November 2026. This step connects the deployed Source audit with the
historical PDF journal and Page 1 extraction batch on the researcher's Windows computer.
It does not claim recovered measurements until original-source review and validated
versioned ingestion actually occur.

## Website and complete worklist

Open `/quality/audit`, set Gap window from/to, and apply. Both pagers and the page-size
form preserve the dates. Dates filter ONLY missing canonical dates: the undated-source
queue and canonical PDF sample plan remain full-history views, explicitly labelled.

The filtered window is clipped to known canonical-history bounds. A window entirely
inside a canonical gap still includes its dates, even with zero canonical records in
that selected window. Non-overlap returns no selected gap dates. Boundary unpublished
or unknown dates outside the canonical history are not invented.

Download complete recovery worklist calls the authenticated server proxy and protected
`GET /api/v1/dataset/recovery-worklist`. The downloaded JSON includes ALL missing dates
in the selected window, regardless of visible page size or page number. Maximum selected
span: 3,660 calendar days. Registered per-date version/source/hint/issue detail limits
remain explicit, with counts and `details_truncated` flags; it is not a promise of
uncapped source details. Historical unregistered local evidence remains outside Neon.

The worklist carries its window, creation time, canonical/missing/exported counts,
evidence assessments, next investigation checks and content ID. The SHA-256 identity
covers rule version, window and items, excluding creation time. A worklist is an
investigation snapshot, not current-state authorization to import/promote or a signed
attestation. Refresh it before eventual ingestion; existing versioned validation and
promotion checks must still run. No API request fetches PDFs or changes records.

## Local reconciliation

`python -m ingestion.reconcile_gaps` requires an explicit worklist and batch folder.
It does not choose the latest batch automatically, because recent/partial/stale batches
can yield misleading coverage. It reads the selected batch's `records/*.json` and opens
`data/raw/bpdb/collection.sqlite3` in SQLite read-only mode. It does not load Neon credentials,
make network calls, reparse PDFs, alter the collection journal or modify original files.

For each missing date, it distinguishes:

- **Exact extraction-date candidates:** an existing extraction record claims that operational
  date. This claim is still a parser result, not independent original-PDF verification.
- **Local extraction hint candidates:** same-day or next-day archive-date hints identify
  possible reports. A candidate can parse to another date, which is explicitly shown.
- **Journal hints only:** known Page 1 URLs near the date, without a matching batch candidate.
- **No local date candidate found:** unknown local evidence, never proof of official PDF absence.

For extraction candidates, original URL/checksum must match a saved journal revision.
All saved revisions are considered, so a later revision cannot hide earlier evidence.
The record's path must match the journal revision, stay inside the chosen raw folder,
exist locally and match both journal byte length and SHA-256. The report retains explicit
failure states for missing revisions, metadata, local files, unsafe/unreadable paths,
path disagreement, size mismatch and checksum mismatch. Matching bytes do not certify
correct dates/values. No candidate is called import-ready.

The generated `local_reconciliation.json` contains the downloaded worklist ID, explicit
selected batch, local metadata fingerprint (journal source/revision rows and batch-record
file hashes), per-date candidates, parser issue codes, file verification states and limits.
Unreadable record JSON is disclosed, not silently treated as a resolved date. Raw parser
exception messages are omitted; only safe error-type/code labels are retained.

Each run writes a NEW uniquely named output folder under `data/processed/gap_recovery`.
No previous investigation or original evidence is overwritten. To compare multiple known
batches, run separately with each explicit batch and retain the reports.

## Windows steps for the actual historical archive

1. On the website, Source audit → Gap window from **2024-01-01**, to **2024-12-31** →
   Apply dates → Download complete recovery worklist. At the 3 November acceptance snapshot,
   there were 75 missing canonical dates in 2024. This count can change after reviewed recovery.
2. Pull the update in the local repository, preserving any local changes:

```bat
cd /d "G:\masters JU\Thesis\bpdb-intelligence"
git pull --ff-only
set "PYTHONPATH=%CD%\backend"
.\.venv-recovery\Scripts\python.exe -m ruff check backend
.\.venv-recovery\Scripts\python.exe -m pytest -q
dir /b data\processed\page1_extraction
```

3. Select the completed historical extraction batch containing `records` for the original
   PDFs. The previously used import batch was
   `a50e4962dea59c8d517795697cc9f4484cafc7089d6c0c6de99930a81af5bf33`.
   Confirm it exists; substitute another explicit completed batch if that is the correct
   local evidence. Do not create an empty folder just to satisfy the command.
4. Assuming the browser saved the worklist in Downloads and the known batch exists:

```bat
.\.venv-recovery\Scripts\python.exe -u -m ingestion.reconcile_gaps --worklist "%USERPROFILE%\Downloads\bpdb-recovery-worklist.json" --batch-folder "data\processed\page1_extraction\a50e4962dea59c8d517795697cc9f4484cafc7089d6c0c6de99930a81af5bf33"
```

If your browser renamed the download, pass the actual filename. Optional `--raw-root`
and `--output-root` accept explicit folder paths if the archive is elsewhere.
5. Expect `status: investigation_only_no_changes`, gap-date count, assessment counts,
   verified-file-state counts and `report_file`. Share the summary and relevant report
   evidence for targeted parser/source investigation; no full archive ZIP is needed.

## Next decisions after the local report

- For exact-date quarantines: inspect PDF date, measurement labels/units and parser issue
  combinations. Fix the parser only against representative real PDFs with regression tests.
- For extracted candidates without canonical records: inspect validation/date-group conflict
  decisions and source versions; do not bypass quarantine or automatically prefer a source.
- For hints: verify the date inside the actual PDF before assigning it to a missing day.
- For missing/local-mismatched files: investigate the original collection journal and URL,
  preserving old revisions and retry provenance. Never treat empty download responses as values.
- After independent review: re-extract using versioned parser output, validate source/date groups,
  stage measurements, verify Neon consistency and preview promotion using existing tooling.
- Re-run missingness and freeze a NEW research snapshot after genuine recoveries. Do not change
  an old frozen bundle or claim estimates as recovered observations.

The deployment environment has the recent Drive checkpoint, not the user's complete 3.77 GiB
historical Windows archive. Full local reconciliation against those actual PDFs must run there;
fixture tests alone do not establish how many of the 75 dates are recoverable.

## Acceptance tests

- Filter a year and ensure missing-date count and displayed dates match Missing data for
  canonical gaps, not all metric-level absent fields. Keep pagination/date-size changes scoped.
- Export from a later page: the JSON must still contain every date once, oldest first.
- Filter a window entirely inside a gap; retain all selected days and zero canonical count.
- Test invalid dates, no overlap and more than 3,660 selected days for worklist export.
- Verify worklist identity; local checker rejects modified, incomplete, duplicate or unsorted dates.
- Test local journal read-only access, original file size/SHA, all revision matching and
  exact-extraction vs archive-hint distinction with controlled fixtures.
- Missing/unsafe/corrupt local evidence must remain unresolved. No automatic imports or estimates.
- Anonymous API/proxy downloads are rejected; server API keys and private storage paths stay hidden.
- Reset clears both visible date controls and applied gap filters.
