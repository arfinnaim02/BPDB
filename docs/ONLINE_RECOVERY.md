# Hosted historical gap investigation

Implemented 3 November 2026. Workflow: **BPDB online gap investigation**,
`.github/workflows/recovery-investigation.yml`. No office checkout or local Python
installation is required to run this workflow. Existing repository DATABASE_URL,
GOOGLE_DRIVE_TOKEN_JSON and GOOGLE_DRIVE_CONFIG_JSON secrets are reused without
printing credentials or changing access permissions.

## Scope

This adds a bounded ONLINE evidence workflow for historical canonical gaps. It is NOT
a complete backup of the home PC's 3.77 GiB historical archive or extraction batches.
Old source bytes which are no longer publicly available and were never archived cannot
be recreated from metadata. No source-supported measurements are claimed as recovered
until the original PDFs and versioned extraction have been reviewed and ingested.

The job reads current canonical gaps from Neon in the existing read-only transaction,
restores only the checksum-verified collection JOURNAL from the existing Drive checkpoint,
and selects Page 1 source URLs using:

- registered gap-linked source evidence and same-day archive hints from the worklist;
- same-day or next-day archive hints in the restored full journal, if those records exist.

The journal may contain historical metadata even though the checkpoint's PDF scope is
recent only. Coverage depends on the actual checkpoint; it is not inferred from local
home-PC counts. No 692-page archive scan, filename guessing, backdated source assignment,
full-history collection or automatic canonical ingestion is performed.

Candidate URLs are deduplicated, sorted by earliest candidate gap/date and URL, and
restricted to the fixed official HTTPS BPDB host, PDF paths, port 443, no credentials,
query strings or fragments. Archive hints remain candidates. Parsed operational dates
are compared with candidate gaps; mismatches remain held.

## Preservation and investigation

1. Prefer an existing Drive blob matching the saved checksum. Download and verify its
   SHA-256 before parsing. If unavailable, retrieve current official bytes with the existing
   verified HTTPS client, bounded retries and 30 MiB response cap. Redirects are not followed.
2. Reject empty/HTML responses without a PDF header. Persist signature-bearing original
   bytes as immutable SHA-addressed Drive blobs, with remote download/hash verification.
   A PDF header is not proof of a readable or authentic report; parsing can still fail.
3. Compare current bytes with the saved expected checksum. Changed source bytes are
   distinguished and held for review; prior archived content is not overwritten.
4. Run the current Page 1 parser and existing numeric validation. Preserve successful,
   quarantined, mismatched and unsupported-layout findings, using safe error-type labels
   rather than raw exception text. No candidate is automatically imported or promoted.
5. Attempt a bounded first-page layout-text diagnostic, preserving its separate Drive blob.
   Extraction may fail; the original PDF is still retained. Text is limited to 100,000
   characters and truncation is disclosed. The text diagnostic is not manual verification.
6. Persist the worklist, candidate plan, investigation report and storage receipt using
   the same remote SHA verification. The daily checkpoint is NEVER pushed/replaced by this job.
   The receipt references preserved evidence; it is an immutable blob, not a dashboard registry.

Offsets bound investigation work, not date coverage. The report includes total candidate
URLs, selected count, offset, next_offset, gaps without known candidates and candidate-plan
fingerprint. When canonical/journal inputs change, candidate order can change: compare
plan/worklist fingerprints rather than blindly assuming an old offset is a stable cursor.

The job is serialized with daily collection using the existing concurrency group. It has
no schedule. A workflow-file push on main starts a small default acceptance run; later
manual runs use the inputs below. An overall 45-minute timeout can interrupt a large or
slow run. Already uploaded PDF blobs remain preserved; summary/report/artifacts may be
incomplete after interruption. Use small batches and inspect failed runs before retrying.

## Online controls

GitHub → arfinnaim02/BPDB → Actions → **BPDB online gap investigation** → Run workflow.
Use main and these initial defaults:

- start_date: 2024-01-01
- end_date: 2024-12-31
- max_files: 10 (choices 5, 10, 20 or 50)
- offset: 0

No custom input is executed as shell code: inputs flow through quoted environment values
and Python's date/integer validation. Windows runners reuse the working HTTPS certificate
store configuration. The existing scheduled collection workflow is unchanged.

## Results and research decisions

The GitHub run summary reports candidate counts, statuses, progress, preserved Drive status
and zero canonical promotions. Diagnostic JSON artifacts are retained for 14 days. Artifact
paths include only the investigation report, summary, worklist, candidate plan, storage
receipt and per-PDF result JSON. Credentials, journal SQLite and original PDF files are
not uploaded as GitHub artifacts. Public BPDB evidence in artifacts is not a secret store.
Longer-lived original PDF/report preservation is in the configured private Drive folder.

A green job means investigation and required preservation completed without reported
retrieval/preservation failures. It does NOT certify recovered data, PDF agreement or
model readiness. Parse failures and held candidates are research findings and can exist
in an otherwise successfully completed investigation. Retrieval/preservation failures
make the job fail AFTER available diagnostics have been written and preserved where possible.
If Drive credentials, checkpoint verification or database access fail first, inspect that
failed step; a successful report cannot be claimed.

Next: inspect actual findings and original PDF evidence, improve only supported parser
cases with real fixtures, resolve source/date conflicts, validate/stage/verify recovered
measurements, preview canonical promotion and generate a NEW research snapshot. The
weekly training treatment must not be used to disguise recoverable source gaps.

## Verification

Automated checks cover URL restrictions, hint vs operational-date distinction,
deduplication, latest journal revision metadata, read-only journal access, archived-byte
reuse, changed bytes/date mismatch holds, empty/HTML rejection, parser failure preservation,
error-text suppression, bounded selection and report/storage receipt integration.
Mocked services in unit tests do not establish real cloud connectivity; the first hosted
acceptance run is the separate integration gate.
