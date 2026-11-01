# Data-management website

## Implemented

The existing Next.js application now has four server-rendered views backed by the Python API:

- Overview: canonical dates, date bounds, calendar gaps and recent daily-worker outcomes.
- Collection history: newest 20/50/100 daily-worker runs, safe counters and workflow link.
- Master dataset: inclusive date filtering, pagination, selectable metric columns and expandable
  version/source/raw-extraction evidence. Measurements remain exact decimal strings.
- Data quality: calendar coverage and non-null metric availability in the latest up to 100 dates.
  The latter is explicitly a recent sample, not full-history metric coverage.

No synthetic data is embedded in the website. API errors and empty datasets have explicit states.
Collection remains automatic through GitHub Actions; the website does not need to stay open.
The browser interface is read-only; manual worker runs are initiated through GitHub's workflow UI.

## Private configuration

Create `frontend/.env.local` from `frontend/.env.example` if you do not already have one.
Preserve existing values when editing an existing file. This file must remain untracked.

| Variable | Meaning |
| --- | --- |
| `BACKEND_URL` | API origin; `http://127.0.0.1:8000` locally; hosted HTTPS API origin in deployment |
| `BACKEND_API_KEY` | Same value as the Python backend's `ADMIN_API_KEY` |
| `DASHBOARD_PASSWORD` | Unique strong workspace password, minimum 12 characters |
| `SESSION_SECRET` | Random signing secret, minimum 32 characters |

Generate a session secret locally with:

```cmd
node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"
```

Keep the generated value private. None of these variables should use a `NEXT_PUBLIC_` prefix.
A missing/short password or signing secret leaves the website on a setup-required sign-in screen.
Signed sessions last eight hours; cookies are HttpOnly, SameSite=Strict and Secure in production.
Use HTTPS in deployment. Rotate SESSION_SECRET to invalidate all sessions. This is a shared
administrator workspace, not multi-user accounts or role-based access. Before public hosting,
configure hosting-layer access controls/rate limiting for sign-in; no durable distributed login
rate limiter is implemented in this commit.

## Windows local startup

Terminal 1, from the repository root:

```cmd
set "PYTHONPATH=%CD%\backend"
.\.venv-recovery\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, from the repository root:

```cmd
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. Enter DASHBOARD_PASSWORD, not the API key.
The frontend sends the API key only from the server to the configured backend. Direct access
to protected pages redirects to sign-in; the CSV proxy also requires a valid session.
The backend must include this commit's CSV endpoint, not just the previous monitoring update.

## CSV contract

`GET /api/v1/dataset/export.csv` is protected by the same backend API key. Optional start_date
and end_date bounds are inclusive. The frontend proxies this through authenticated `/api/export`.
Both layouts export all matching canonical dates and all supported national metrics, independent of table page size
or selected visible columns. Dates are ordered ascending. The default daily layout has one date per row;
the separate evidence layout has one measurement per row. Nulls are empty cells; units, period, fuel, source URL/page/checksum and version are included.

All records are read within one PostgreSQL repeatable-read read-only transaction. Materialization
is bounded to 10,000 dates; larger exports return 422 and should use the existing export CLI.
The evidence CSV includes export timestamp and version IDs; HTTP headers include export byte checksum,
canonical-date count and measurement count. It is not registered as a durable DatasetVersion.
Checksums cover timestamped CSV bytes, so independent exports need not have identical checksums.
Text cells that could execute spreadsheet formulas get a leading apostrophe; numeric measurements
are unchanged. Original raw evidence remains unchanged in Neon and visible in the dataset API.

## Acceptance checks

1. Unauthenticated page access redirects to sign-in. Wrong password fails; sign-out removes access.
2. Overview matches current authenticated API summary; do not expect a fixed historical count.
3. Collection table matches API runs and selected limit; Drive status is not inferred from worker status.
4. Dataset date filters and next/previous links work. Selected columns survive page navigation.
5. Expand source evidence, open an original PDF and compare a measurement/unit against that PDF.
6. Download CSV for one known date; compare row values and provenance with the daily API.
   Repeat without date filters to obtain the complete current national master export.
7. Data quality uses observed calendar coverage; recent metric availability is labelled with sample size.
8. Test on desktop and mobile widths; check navigation, horizontal tables, evidence expansion and forms.
9. Stop the API and reload a page: a service error must appear instead of sample/stale records.
10. Check browser network/source: no BACKEND_API_KEY, SESSION_SECRET or database URL should be present.

## Verification for this update

- Backend: 44 tests passed, 1 dedicated PostgreSQL integration test skipped; Ruff and compilation passed.
- Frontend: session tampering/expiry, filter validation, pagination and safe-link tests passed;
  TypeScript and Next.js production build passed.
- Browser QA could not run: managed preview passed Vite-specific `--host`/`--strictPort` options
  to Next.js, which rejected them. No layout/browser acceptance is claimed.
- Live Neon/browser acceptance and deployment remain required. No production credentials were used.

## Deployment boundary

This update commits application code, not a deployment. Vercel can build `frontend` as the Next.js
root, with the four private variables set in its environment. `BACKEND_URL` must point to a reachable
hosted Python API; localhost on Vercel cannot reach your computer. Choose and verify that API host
before considering deployment complete. Neon and the GitHub worker remain authoritative.


## Daily analysis CSV update

The default website download is now a wide, values-only daily table: Operational Date plus
13 metric columns, with descriptive English headings and units. Dates are ISO YYYY-MM-DD,
ordered oldest first; missing values stay blank and numeric zero remains zero. Decimal strings
are formatted without redundant trailing zeroes, preserving their exact numeric values.
No source URLs, UUIDs, raw extraction text or export timestamps are included in these data rows.
The UTF-8 BOM improves spreadsheet recognition. CSV cannot preserve visual styling or column widths.

Use Source evidence CSV for the existing long-format export with provenance. The backend
HTTP export defaults to layout=daily; layout=evidence selects the detailed export. The internal
export_csv helper retains evidence as its default for backward-compatible internal callers.
Both downloads cover all filtered dates and use a consistent read-only transaction. Neither
changes the underlying Neon records. Unsupported metric/unit/period/fuel combinations fail
closed in the daily format instead of being silently combined or discarded.

Acceptance: download a small date range and compare each day's columns with the master table;
check blank versus zero values and verify the separate evidence download. Restart both servers
after pulling this update.
