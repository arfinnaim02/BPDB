# Source inventory — provisional, 2026-10-25

Official archive: https://misc.bpdb.gov.bd/daily-generation-archive

| Item | Evidence | Status |
|---|---|---|
| Categories: Page 1, Page 2, Page 3, Summary, Energy, Load | Indexed official page 24 text | Category names supported; PDFs uninspected |
| Pagination query: ?page=N | Indexed official archive URLs | Exact current HTML pending |
| Archive dates displayed as dd/mm/yyyy | Indexed official page rows | Stored as hints only |
| Direct archive HTTP retrieval | curl request returned HTTP 503 | Blocked in current environment |
| Modern/legacy PDF layouts | No PDF supplied or successfully retrieved | Not verified |
| Operational date vs publication date | No original PDFs inspected | Not verified |
| Legacy CSV coverage | 556 rows, 2025-01-01 to 2026-07-10, structurally audited | Original-PDF validation and corrections still pending |

Discovery supports same-origin HTTPS PDF anchors, relative links, query strings, table
header categories and bounded numeric page links. Unknown structures stay unknown or
fail clearly; they must not silently be treated as complete collection.

The test fixture is synthetic, explicitly labeled and contains no measured BPDB values.
It proves parser behavior for a known structure, not compatibility with the live archive.
The collector currently fails the run if no PDF links are found. A legitimate empty
archive result and a changed layout need explicit future source-specific handling.

## Required before the ingestion phase can be accepted

1. Save authentic archive HTML with retrieval time and checksum.
2. Confirm header/date/link structure and pagination ordering.
3. Retrieve representative PDF categories from modern and legacy periods.
4. Confirm operational dates inside PDFs, units, totals and publication delays.
5. Record each proven field with page, label, unit and source URL.
6. Independently compare extracted values to originals before canonical ingestion.
