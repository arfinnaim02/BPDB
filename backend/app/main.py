import hmac
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from app.api.audit import router as audit_router
from app.api.monitoring import router as monitoring_router
from app.api.quality import router as quality_router
from app.core.config import get_settings
from app.db.session import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if get_engine.cache_info().currsize:
        get_engine().dispose()


app = FastAPI(title="BPDB Intelligence API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET"],
    allow_headers=["X-API-Key"],
)


class HealthResponse(BaseModel):
    status: str
    service: str = "bpdb-intelligence"


def require_admin(x_api_key: Annotated[str | None, Header()] = None) -> None:
    expected = get_settings().admin_api_key
    if not expected or not expected.get_secret_value():
        raise HTTPException(503, "Administrative access is not configured")
    if not x_api_key or not hmac.compare_digest(
        x_api_key.encode(), expected.get_secret_value().encode()
    ):
        raise HTTPException(401, "Invalid API key")


app.include_router(monitoring_router, dependencies=[Depends(require_admin)])
app.include_router(quality_router, dependencies=[Depends(require_admin)])
app.include_router(audit_router, dependencies=[Depends(require_admin)])


@app.get("/health/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/health/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    if get_settings().database_url is None:
        raise HTTPException(503, "Database is not configured")
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if revision != "0002_environment_observations":
                raise RuntimeError("Migration pending")
    except Exception:
        # Never return driver exception text; it can contain credentials or connection details.
        raise HTTPException(503, "Database unavailable or migrations pending") from None
    return HealthResponse(status="ready")


@app.get("/api/v1/system", dependencies=[Depends(require_admin)])
def system() -> dict:
    return {
        "phase": "data_management",
        "collection_schedule": "12:00 Asia/Dhaka",
        "scheduler_implemented": True,
        "parser_implemented": True,
    }



