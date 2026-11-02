# Registered evidence audit — November 2, 2026

## What this feature does

The authenticated GET /api/v1/dataset/audit and /quality/audit website page investigate missing
canonical dates using existing Neon metadata. Open Data Quality → Investigate sources.
No schema change, new credential, scraping, file reparse, promotion or database write is performed.

Three views:
1. Missing canonical dates with registered report versions, Page 1 source metadata and extraction issues.
2. Registered held Page 1 sources without report-date metadata or any national report-version link.
3. A deterministic original-PDF comparison plan with links, checksums, version IDs and canonical
   measurements/raw evidence. Verification is explicitly NOT recorded or certified by the page.

## Evidence rules

Calendar gaps are restricted to the span of current validated national_daily canonical records.
Gap dates are paginated individually, oldest first. The date-page calculation traverses contiguous
ranges instead of expanding every missing day in memory.

For a gap date, report/version links are restricted to national_daily reports. A source is shown in
date-linked metadata if it has SourceDocument.report_date equal to the date or is linked to a
registered national version for that date. Report-date metadata itself still needs original-PDF
verification; it is not an independently confirmed operational date.

SourceDocument.archive_date_hint alone is ONLY a candidate association. It can describe another
operational/reporting date and never establishes a gap's cause. Hint-only sources do not contribute
date-linked issue findings. An issue attached to a different version is not reassigned via its source.

Findings report actual registered states: partial/quarantined/conflict/validated noncanonical versions,
held source status, and unresolved issues. They do not infer why a report was not promoted.
Official source-report availability remains not_assessed even where metadata exists.

No date-linked evidence in Neon does NOT mean no PDF exists. Historical local batch quarantine/failure
records and failed downloads may never have been registered in Neon. Missing operational-date metadata
also prevents a date-level match. The undated queue is not a complete count of all historical problems.

## Privacy and pagination

Raw ExtractionIssue.details, driver errors, local storage keys and credentials are not returned.
Issue output whitelists code, severity, source/version IDs, resolved flag and sanitized nested check
codes. Original PDF URLs/checksums and sample raw measurement evidence remain intentionally available.

- gap_page: 1–100000; gap_page_size: 1–50, default 20 (website choices 10/20/50).
- source_page: 1–100000; undated queue has 10 sources per page.
- Per date, at most 10 versions, 10 date-linked sources, 10 hint candidates and 20 issues are shown.
  True counts are returned/displayed, so capped details are explicit rather than silently omitted.
- Out-of-range pages return empty items and retain totals.
- Both paginations preserve one another in the website.
- Read-only repeatable-read session, existing statement timeout and no-store responses apply.
  Separate page requests may observe later database updates.

## PDF verification plan

Candidate dates are the first and last canonical date in each observed year. A year with one date
contributes one sample. If more than 32 candidates exist, an evenly spaced deterministic subset
retains the overall first/last dates. This is targeted evidence review, not a random accuracy estimate.

Layouts must be checked inside PDFs; stored parser/version keys are not assumed to identify layouts.
The policy aims for historical coverage but does not guarantee every layout or unusual case is included.
Canonical measurements include exact units, source-page references and raw extraction snippets.
If canonical sample evidence fails an integrity check, the page still returns gap evidence and reports
a generic sample-consistency warning; it does not fabricate or silently certify a sample.

For each PDF:
1. Confirm operational date and layout, distinguishing reporting date where present.
2. Compare generation, demand, maximum generation and energy, plus available modern cost/other fields.
3. Check numeric signs, separators, units and any MWh to million-kWh conversion.
4. Record agreement/disagreement/unreadable evidence with URL, SHA-256 and report-version ID.
5. Resolve discrepancies through reviewed versioning; never overwrite original source values.

This update does not implement saved human verification results or automatic repairs.
An independent review ledger and original-file inspection remain future work.

## Tests and deployment acceptance

Local validation: 69 backend tests passed, 1 opt-in PostgreSQL integration skipped; 4 frontend tests,
TypeScript, production build, Ruff, compilation and dependency consistency passed.
Tests cover exact/hint-only associations, report/zone scope, unrelated version issues, privacy,
resolved flags, pagination/caps, deterministic sample selection, sample integrity errors and auth.

Live Neon values and original PDFs were not accessed while implementing this feature. No original-PDF
measurement has been newly verified by adding the page. Browser preview remains unverified because
the existing managed preview cannot launch this Next.js app with its supplied CLI flags.

Wait for both Vercel projects to deploy the new commit, then:
- Open Data Quality → Investigate sources.
- Reconcile the missing-date total and bounds with Data Quality.
- Inspect one registered-evidence, hint-only and unknown date if present.
- Open source details and confirm hints are labelled as possible matches only.
- Review the undated queue without interpreting zero as proof all local failures are resolved.
- Open a planned PDF and manually compare the displayed measurements.
- Check desktop/mobile behavior and pagination. No environment or migration changes are needed.

Next: inspect original sources and local batch evidence, record independent findings, then decide
which gaps can be repaired and which variable/date ranges are defensible for analytical research.
