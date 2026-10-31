from app.core.config import Settings
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


def test_health_and_unconfigured_readiness():
    app.dependency_overrides.clear()
    # main uses cached settings directly; override the cache via monkeypatch in next tests.
    with TestClient(app) as client:
        assert client.get("/health/live").json()["status"] == "ok"


def test_unconfigured_database(monkeypatch):
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(_env_file=None))
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 503
        assert client.get("/api/v1/system").status_code == 503


def test_admin_auth(monkeypatch):
    settings = Settings(_env_file=None, admin_api_key="test-only-value")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(app) as client:
        assert client.get("/api/v1/system").status_code == 401
        assert client.get("/api/v1/system", headers={"X-API-Key": "wrong"}).status_code == 401
        response = client.get("/api/v1/system", headers={"X-API-Key": "test-only-value"})
        assert response.json()["scheduler_implemented"] is False


def test_readiness_migration_check(monkeypatch):
    settings = Settings(
        _env_file=None, database_url="postgresql+psycopg://test:test@localhost/test"
    )
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    # Keep the original cached function for lifespan; patch only during each request.
    with TestClient(app) as client:
        with monkeypatch.context() as patch:
            patch.setattr("app.main.get_engine", lambda: engine)
            assert client.get("/health/ready").status_code == 503
            with engine.begin() as c:
                c.execute(text("CREATE TABLE alembic_version (version_num TEXT)"))
                c.execute(text("INSERT INTO alembic_version VALUES ('0001_foundation')"))
            assert client.get("/health/ready").status_code == 503

            with engine.begin() as c:
                c.execute(text(
                    "UPDATE alembic_version "
                    "SET version_num='0002_environment_observations'"
                ))

            assert client.get("/health/ready").json()["status"] == "ready"
    engine.dispose()


def test_config_tls_and_driver():
    import pytest
    from pydantic import ValidationError

    for url in [
        "postgresql://test:test@localhost/test",
        "postgresql+psycopg://test:test@ep-test.neon.tech/db",
    ]:
        with pytest.raises(ValidationError) as exc:
            Settings(_env_file=None, database_url=url)
        assert "test:test" not in str(exc.value)
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://test:test@ep-test.neon.tech/db?sslmode=require",
    )
    assert "test:test" not in repr(settings)
