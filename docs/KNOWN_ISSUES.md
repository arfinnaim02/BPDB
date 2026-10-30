# Known issues and limitations

1. No Neon credentials were supplied. Live connection, upgrade execution and PostgreSQL
   concurrency behavior are unverified. Configure DATABASE_URL locally; do not post it in chat.
2. Official archive fetch returned HTTP 503. Actual HTML, PDF layouts, units, source dates,
   publication lag and historical source coverage are not verified. A legacy CSV was structurally audited;
   see EXISTING_CODE_AUDIT.md for scale/date concerns and limitations.
3. Discovery fixtures are synthetic. Unknown download endpoints, externally hosted originals,
   merged table headers or a changed page structure will require audited parser extensions.
4. Downloader, PDF extraction, validation, end-to-end ingestion, backfill, CSV export,
   schedule, analytics, ML, decisions, PDF reporting and thesis generation are not implemented.
5. Schema has no database-level immutable-row privileges/triggers yet. Canonical promotion
   trusts internal quality/review decisions; there is deliberately no public promotion endpoint.
6. Source/version membership consistency and date/metric/unit reconciliation belong to
   the Day 2 validation service and must pass before real data is accepted.
7. Readiness's expected revision must advance when future migrations are added.
8. Runtime tested on Linux Python 3.12 / Node 24. Windows commands are provided but not
   executed on Windows in this environment.
9. Current FastAPI/Starlette emits one upstream TestClient/httpx deprecation warning.
   Tests pass; a future dependency update may require the newer client adapter.
