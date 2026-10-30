# BPDB Intelligent Power Analytics

Day 1 foundation for the master's thesis platform. Read docs/PROJECT_STATUS.md for
what is verified and docs/KNOWN_ISSUES.md for explicit blockers. No sample operational
data, fictional model metrics or precomputed research conclusions are included.

Start with **docs/WINDOWS_SETUP.md**. The project is extracted as bpdb-intelligence.
Python 3.12 and Node.js 20.9+ are required; Node 24 was used for local verification.

## Implemented

- FastAPI live/readiness endpoints; readiness checks database and migration revision.
- API-key-protected administrative status endpoint, closed when no key is configured.
- SQLAlchemy lineage schema and a frozen initial Alembic migration.
- Canonical version promotion with correction safeguards and transaction ownership.
- Bounded, same-origin PDF-link discovery with retry and explicit no-document failure.
- Next.js / TypeScript / Tailwind health screen using actual API responses.
- Automated tests and a CI workflow; no scheduler is installed by this workflow.

## API

| Route | Access | Behavior |
|---|---|---|
| GET /health/live | Public | Process alive, even without database |
| GET /health/ready | Public | 200 only with reachable migrated database; otherwise 503 |
| GET /api/v1/system | X-API-Key | Current implemented phase and schedule configuration intent |
| GET /docs | Local development | Interactive API documentation |

Prior work and dataset audit: docs/EXISTING_CODE_AUDIT.md.
Architecture and planned schema: docs/ARCHITECTURE.md.
Source evidence: docs/SOURCE_INVENTORY.md. Field definitions: docs/DATA_DICTIONARY.md.
Required phase checklist: docs/IMPLEMENTATION_CHECKLIST.md.

## Portable verification (from repository root)

```text
python -m pytest -q
python -m ruff check backend
python -m alembic -c backend/alembic.ini upgrade head --sql
```

The last command requires DATABASE_URL but generates SQL only; it does not connect or
apply a migration. Use the actual upgrade command in the Windows guide to apply it.
Dependencies are pinned in backend/requirements-tested.txt and frontend/package-lock.json.
Do not commit .env, raw data, credentials or node_modules. Test fixtures are explicitly
synthetic and cannot be used as research data.
