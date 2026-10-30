# Windows 11 setup — PowerShell

Extract the ZIP into your chosen project location. Open PowerShell in **bpdb-intelligence**.
Use Python 3.12 and Node 20.9+ (Node 24 was used here). These commands avoid activation
so PowerShell execution-policy changes are unnecessary. All backend commands below run
from the repository root unless stated otherwise.

## 1. Install backend

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-tested.txt
Copy-Item .env.example .env
notepad .env
```

In .env replace DATABASE_URL with your Neon connection string, using
`postgresql+psycopg://` and `sslmode=require`. URL-encode reserved characters in the password.
Prefer a direct Neon endpoint for migrations. A pooled runtime endpoint can be configured
later for deployed services. Keep the whole connection string local.

Generate an admin key; paste the output into ADMIN_API_KEY in .env:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

Do not set administrative secrets in frontend environment variables.

## 2. Apply the initial migration to your project database

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini check
```

Expected revision: `0001_foundation`. The migration creates core tables; it does not
populate observations. Run these on a fresh project database or branch, not an unrelated
existing schema. No live Neon migration was performed during package preparation.

## 3. Test and run backend

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Open another PowerShell terminal at the repository root:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

Expected: live status `ok`; ready status `ready` only after successful database setup.
If ready returns 503, verify .env, SSL and migrations locally. Client responses intentionally
omit driver exceptions so they cannot reveal secrets. API docs: http://127.0.0.1:8000/docs.

## 4. Install and run frontend (new terminal)

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run typecheck
npm run build
npm run dev
```

Optional runtime integration check after the production build, from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\smoke.py
```

It launches temporary API/frontend processes on ports 18000 and 13000 and cleans them up.

Visit http://localhost:3000. The page shows backend and database health; it does not display
operational measurements yet. If backend is stopped it shows a pending/unreachable state.

## 5. Check actual archive discovery

In another terminal at the repository root:

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m ingestion.discovery --max-pages 1 --output source-inventory.json
Remove-Item Env:PYTHONPATH
```

A successful invocation produces actual source URLs. A failure exits with code 1 and a
sanitized error type. The BPDB request returned HTTP 503 from the preparation environment;
try locally and inspect the actual HTML before accepting live-source compatibility.
No PDFs are downloaded or parsed by this Day 1 command.

## Optional PostgreSQL integration test (isolated schema)

Configure TEST_DATABASE_URL for a dedicated test database/Neon branch, never production.
It must permit CREATE SCHEMA. The test creates a random schema, applies the actual migration,
checks drift/constraints and drops that schema in a finally block. A failed cleanup can leave
a schema with prefix bpdb_test_; inspect your test branch if the process is interrupted.

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST/TESTDB?sslmode=require"
.\.venv\Scripts\python.exe -m pytest backend\tests\test_postgres.py -q
Remove-Item Env:TEST_DATABASE_URL
```

## Next phase

Verify Neon readiness, obtain authentic archive/PDF examples, then build and independently
verify parsers and source-preserving ingestion before historical backfill or ML training.
