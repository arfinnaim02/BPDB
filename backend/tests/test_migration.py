from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from app.core.config import get_settings


def test_postgres_migration_sql(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    get_settings.cache_clear()
    try:
        out = StringIO()
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"), output_buffer=out)
        command.upgrade(config, "head", sql=True)
        sql = out.getvalue()
        assert sql.count("CREATE TABLE") == 16  # 15 application tables plus Alembic ledger
        assert "CREATE TABLE environment_observations" in sql
        assert "0002_environment_observations" in sql
        assert "CREATE TABLE research_forecasts" in sql
        assert "CREATE TABLE research_forecast_outcomes" in sql
        assert "uq_research_forecast_input" in sql
        assert "0003_research_forecasts" in sql
        assert "ALTER TABLE daily_reports ADD CONSTRAINT fk_daily_current_version" in sql
        assert "UNIQUE (report_date, dataset_grain)" in sql
    finally:
        get_settings.cache_clear()

