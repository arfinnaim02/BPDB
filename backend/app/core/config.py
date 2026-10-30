from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", extra="ignore", hide_input_in_errors=True
    )
    database_url: SecretStr | None = None
    admin_api_key: SecretStr | None = None
    cors_origins: list[str] = ["http://localhost:3000"]
    bpdb_archive_url: str = "https://misc.bpdb.gov.bd/daily-generation-archive"
    discovery_max_pages: int = Field(default=2, ge=1, le=20)
    http_timeout_seconds: float = Field(default=25, ge=1, le=120)

    @field_validator("database_url")
    @classmethod
    def database_dialect(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None or not value.get_secret_value():
            return None
        try:
            url = make_url(value.get_secret_value())
        except Exception:
            raise ValueError("Invalid database URL") from None
        if url.drivername != "postgresql+psycopg":
            raise ValueError("Use postgresql+psycopg:// with the psycopg 3 driver")
        if url.host and url.host.endswith(".neon.tech"):
            if url.query.get("sslmode") not in {"require", "verify-full", "verify-ca"}:
                raise ValueError("Neon requires TLS: set sslmode=require or stronger")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
