# Vercel deployment — two projects, one repository

Architecture: Next.js frontend on Vercel; FastAPI HTTP API on Vercel; Neon master database;
existing GitHub Actions scheduled worker; Google Drive collection persistence.
The collector is not started by a web request or Vercel build. No new migration or historical
reimport is needed. Both web projects are deployed from main of arfinnaim02/BPDB.

## 1. Import the API first

In Vercel: Add New → Project → import arfinnaim02/BPDB.

- Project name: choose an available name, e.g. bpdb-api.
- Root Directory: backend.
- Framework Preset: FastAPI (auto-detected).
- Python version: 3.12 via the committed .python-version.
- Install/build/output settings: retain framework defaults. Do not set a Uvicorn start command.
- Entrypoint: app/main.py, exporting app; supported by Vercel's FastAPI detection.
- backend/vercel.json configures a 60-second maximum duration.

Add these private environment variables for Production:

| Variable | Value |
| --- | --- |
| DATABASE_URL | Existing Neon SQLAlchemy psycopg connection string with SSL enabled |
| ADMIN_API_KEY | Existing private backend admin API key; must match frontend BACKEND_API_KEY |

GitHub Actions secrets do NOT automatically populate Vercel environment variables.
Do not include quotation marks around values pasted into Vercel's separate value fields.
Do not add Google OAuth/Drive tokens or PDFs to this project.

Deploy. Use the returned stable production domain, not a guessed example hostname.
Visit /health/live (expected ok) and /health/ready (expected ready).
The readiness check verifies database connectivity and migration 0002_environment_observations.
Use /docs to test dataset/summary with the private x-api-key. Never put the key in a URL.

A 404 at the API domain root is not the health check. Test the full /health/live path.
A 503 readiness result needs database/SSL/migration investigation before deploying the frontend.
Do not run migrations automatically during Vercel build/startup.

## 2. Import the frontend separately

Create another Vercel project and import the SAME repository again.

- Project name: choose an available name, e.g. bpdb-intelligence.
- Root Directory: frontend.
- Framework Preset: Next.js.
- Node.js version: 24.x.
- Install Command: npm ci.
- Build Command: npm run build.
- Output Directory: framework default.

Add these private environment variables for Production:

| Variable | Value |
| --- | --- |
| BACKEND_URL | API's stable production HTTPS origin, without /docs or /api/v1 |
| BACKEND_API_KEY | Exactly the API project's ADMIN_API_KEY |
| DASHBOARD_PASSWORD | Unique workspace password, minimum 12 characters |
| SESSION_SECRET | Private random signing secret, minimum 32 characters |

Generate a new signing secret locally using node -e
"console.log(require('node:crypto').randomBytes(32).toString('hex'))".
Do not share the generated value. Do not use NEXT_PUBLIC_ prefixes.
Do not add DATABASE_URL or Drive tokens to the frontend.

Deploy and open the returned production URL. Sign in using DASHBOARD_PASSWORD.
A localhost BACKEND_URL cannot reach your computer from Vercel.

## 3. Acceptance

- Sign-in works over HTTPS; sign-out and unauthenticated page access are protected.
- Overview matches the API's current Neon canonical count/date bounds.
- Collection history loads; Drive outcome is verified separately in GitHub.
- Master dataset filters, pagination, source PDF links and exact values work.
- Daily CSV for a known date matches the master record.
- Complete daily CSV download works for the currently supported archive size.
- Data-quality page labels recent metric availability as a sample.
- Check desktop/mobile layouts and production runtime logs.
- Close local backend/frontend terminals; reload the hosted website to verify independence.
- Confirm a later GitHub Actions scheduled run updates records visible through the website.

## Operational boundaries and troubleshooting

Both projects must serve production requests. If Vercel Deployment Protection intercepts backend
requests, resolve that protection configuration for server-to-server production calls.
The API's X-API-Key authentication must remain enabled. Do not expose keys in query strings.
Frontend calls are server-to-server, so a browser CORS change is not required for this architecture.

The API is read-only for dataset requests; the worker is the writer. Use a Neon pooled connection
if appropriate for your deployment. Provision separate preview/test database credentials if you
enable database-backed Preview deployments; this guide configures Production only.

Vercel applies function execution, memory, payload and plan usage limits. The API refuses CSV
responses larger than 4,000,000 bytes on Vercel with an explicit 422. Large source-evidence exports
may require narrower date filters or the existing local export CLI. Normal daily values CSVs are
much smaller than evidence CSVs. The frontend export handler has a 60-second duration setting;
API request timeout remains 25 seconds. A cold start may require a retry; inspect logs if repeated.

The shared workspace password is not a multi-user identity system. Configure available hosting
access/firewall controls for internet exposure; no durable distributed login rate limiter is
implemented. Rotate SESSION_SECRET to invalidate all sessions when needed.

After editing environment variables, redeploy the affected project. Connecting GitHub enables
future main commits to trigger Vercel deployments; no manual code upload is needed.
Hobby usage is subject to Vercel's current plan allowances; no unlimited free hosting claim is made.

## Evidence

Repository preparation and local automated checks do not verify an actual Vercel deployment.
Record the two returned deployment URLs and test the above acceptance checks before marking
hosting complete. No Vercel account operation or production secret was used while preparing this.

Official references (checked November 1, 2026):
- https://vercel.com/docs/frameworks/backend/fastapi
- https://vercel.com/docs/functions/runtimes/python
- https://vercel.com/docs/functions/limitations
