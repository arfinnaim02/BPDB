# Data-management API

All routes below require `X-API-Key` matching the server-side `ADMIN_API_KEY`.
Do not put this key into frontend browser code or a `NEXT_PUBLIC_*` variable.
`/health/live` and `/health/ready` remain public. No new migration is required.

| GET route | Query | Result |
| --- | --- | --- |
| `/api/v1/dataset/summary` | None | Current validated national date count, bounds and calendar gaps |
| `/api/v1/collection/runs` | `limit=20` (1–100) | Latest daily-worker runs, newest first; safe counters and scan outcomes |
| `/api/v1/dataset/daily` | `start_date`, `end_date`, `page=1`, `page_size=20` | Current validated national records with version/source/measurement evidence |

Dates use ISO `YYYY-MM-DD`; bounds are inclusive. `page` is 1–100000 and `page_size` is
1–100. Daily records sort by operational date descending. An empty or out-of-range page
returns an empty `items` list; `total_dates` and `total_pages` describe the filtered result.
Reversed dates, malformed dates and out-of-bounds parameters return 422.
Missing/incorrect keys return 401 when admin access is configured; absent configuration returns 503.

Values are decimal strings, not rounded floats. Null values and unknown availability times
remain null. Each measurement includes its own source ID/page, raw text, unit, period, zone
and fuel dimension where applicable. Linked sources include official URL and checksum;
private local/storage paths are excluded. Missing source linkage, duplicate metric grains
or empty canonical measurements fail closed with 503. Database errors return generic 503.

Successful responses use `Cache-Control: no-store`. PostgreSQL requests are read-only,
repeatable-read with a 15-second per-statement timeout. This gives consistency within one
request, not a frozen snapshot across different page requests. Use a versioned database
export for research reproducibility.

Worker history intentionally excludes raw statistics and driver errors. Drive persistence
is separate from the worker: `not_recorded_in_ingestion_run` means consult the GitHub
workflow's Drive checkpoint outcome, not that persistence failed or succeeded.

## Windows CMD acceptance

First preserve any local uncommitted work before pulling; do not discard it.
From the project folder, after synchronizing the repository:

```cmd
set "PYTHONPATH=%CD%\backend"
.\.venv-recovery\Scripts\python.exe -m ruff check backend
.\.venv-recovery\Scripts\python.exe -m pytest -q
.\.venv-recovery\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Configure DATABASE_URL and ADMIN_API_KEY privately in the existing environment/.env.
Open `http://127.0.0.1:8000/docs`; use **Try it out** and the `x-api-key` field:

1. Summary returns 200 and expected canonical bounds/count (use current Neon, not fixed numbers).
2. Runs with limit=5 returns daily-worker history; verify a scheduled trigger against GitHub.
3. Daily with page_size=2 returns two dates, source checksums and decimal-string measurements.
4. Page=2 returns subsequent dates; test on an unchanged dataset to compare non-overlap.
5. Equal start/end bounds for a known date return exactly that date.
6. Reversed dates and page_size=101 return 422; missing/wrong key returns 401.
7. Confirm no secret/storage path is exposed and responses contain `Cache-Control: no-store`.

The existing `ingestion.export_master` CLI still produces database-derived CSVs.
An HTTP CSV endpoint and the real-data frontend are separate next work items.
