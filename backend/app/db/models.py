"""Core lineage schema. Numeric observations are immutable and attached to versions."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IngestionRun(Identity, Base):
    __tablename__ = "ingestion_runs"
    status: Mapped[str] = mapped_column(String(20), default="running")
    trigger: Mapped[str] = mapped_column(String(20))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    statistics: Mapped[dict] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(80))
    __table_args__ = (
        CheckConstraint("status IN ('running','succeeded','failed','partial')", name="status"),
    )


class SourceDocument(Identity, Base):
    __tablename__ = "source_documents"
    original_url: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    report_date: Mapped[date | None]
    archive_date_hint: Mapped[date | None]
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    parser_version: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="downloaded")
    ingestion_run_id: Mapped[str] = mapped_column(ForeignKey("ingestion_runs.id"))
    __table_args__ = (
        UniqueConstraint("original_url", "sha256", name="uq_source_url_checksum"),
        CheckConstraint("size_bytes > 0", name="positive_size"),
        CheckConstraint("length(sha256) = 64", name="checksum_length"),
    )


class DailyReport(Identity, Base):
    __tablename__ = "daily_reports"
    report_date: Mapped[date] = mapped_column(index=True)
    dataset_grain: Mapped[str] = mapped_column(String(80), default="national_daily")
    current_version_id: Mapped[str | None] = mapped_column(String(36))
    __table_args__ = (
        UniqueConstraint("report_date", "dataset_grain", name="uq_daily_report_grain"),
        ForeignKeyConstraint(
            ["id", "current_version_id"],
            ["daily_report_versions.report_id", "daily_report_versions.id"],
            name="fk_daily_current_version",
            use_alter=True,
        ),
    )


class ReportVersion(Identity, Base):
    __tablename__ = "daily_report_versions"
    report_id: Mapped[str] = mapped_column(ForeignKey("daily_reports.id"), index=True)
    version_number: Mapped[int]
    quality_status: Mapped[str] = mapped_column(String(20))
    parser_version: Mapped[str] = mapped_column(String(80))
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correction_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("report_id", "version_number", name="uq_report_version_number"),
        UniqueConstraint("report_id", "id", name="uq_report_version_identity"),
        CheckConstraint("version_number > 0", name="positive_version"),
        CheckConstraint(
            "quality_status IN ('validated','partial','quarantined','conflict')",
            name="quality_status",
        ),
    )


class VersionSource(Base):
    __tablename__ = "version_sources"
    version_id: Mapped[str] = mapped_column(
        ForeignKey("daily_report_versions.id"), primary_key=True
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"), primary_key=True)


class ExtractionIssue(Identity, Base):
    __tablename__ = "extraction_issues"
    source_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"), index=True)
    version_id: Mapped[str | None] = mapped_column(ForeignKey("daily_report_versions.id"))
    code: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Measurement:
    version_id: Mapped[str] = mapped_column(ForeignKey("daily_report_versions.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"))
    metric: Mapped[str] = mapped_column(String(100))
    zone: Mapped[str] = mapped_column(String(80), default="national")
    period: Mapped[str] = mapped_column(String(80), default="daily")
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    unit: Mapped[str] = mapped_column(String(40))
    source_page: Mapped[int | None]
    raw_text: Mapped[str | None] = mapped_column(Text)


class GenerationObservation(Identity, Measurement, Base):
    __tablename__ = "generation_observations"
    __table_args__ = (
        UniqueConstraint(
            "version_id", "metric", "zone", "period", "unit", name="uq_generation_grain"
        ),
    )


class DemandObservation(Identity, Measurement, Base):
    __tablename__ = "demand_observations"
    __table_args__ = (
        UniqueConstraint("version_id", "metric", "zone", "period", "unit", name="uq_demand_grain"),
    )


class FuelObservation(Identity, Measurement, Base):
    __tablename__ = "fuel_observations"
    fuel: Mapped[str] = mapped_column(String(80))
    __table_args__ = (
        UniqueConstraint(
            "version_id", "metric", "zone", "period", "unit", "fuel", name="uq_fuel_grain"
        ),
    )


class CostObservation(Identity, Measurement, Base):
    __tablename__ = "cost_observations"
    fuel: Mapped[str] = mapped_column(String(80), default="all")
    __table_args__ = (
        UniqueConstraint(
            "version_id", "metric", "zone", "period", "unit", "fuel", name="uq_cost_grain"
        ),
    )


class LoadSheddingObservation(Identity, Measurement, Base):
    __tablename__ = "load_shedding_observations"
    __table_args__ = (
        UniqueConstraint(
            "version_id", "metric", "zone", "period", "unit", name="uq_load_shedding_grain"
        ),
    )

class EnvironmentObservation(Identity, Measurement, Base):
    __tablename__ = "environment_observations"
    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "metric",
            "zone",
            "period",
            "unit",
            name="uq_environment_grain",
        ),
    )



class DatasetVersion(Identity, Base):
    __tablename__ = "dataset_versions"
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    cutoff_date: Mapped[date]
    row_count: Mapped[int]
    # Frozen membership, not a query over whatever is current during export.
    member_version_ids: Mapped[list] = mapped_column(JSON)
    export_storage_key: Mapped[str | None] = mapped_column(Text)


class ResearchForecast(Base):
    """Append-only prospective issues; never authoritative source measurements."""

    __tablename__ = "research_forecasts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(64), index=True)
    model_experiment_id: Mapped[str] = mapped_column(String(64))
    target_date: Mapped[date] = mapped_column(index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20))
    prediction: Mapped[Decimal | None] = mapped_column(Numeric(24, 9))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (
        UniqueConstraint(
            "model_id", "target_date", "input_fingerprint", name="uq_research_forecast_input"
        ),
        CheckConstraint("status IN ('forecast','withheld')", name="status"),
        CheckConstraint(
            "(status = 'forecast' AND prediction IS NOT NULL AND prediction > 0) OR "
            "(status = 'withheld' AND prediction IS NULL)",
            name="prediction_state",
        ),
        CheckConstraint(
            "length(id) = 64 AND length(model_id) = 64 AND length(input_fingerprint) = 64",
            name="fingerprints",
        ),
    )


class ResearchForecastOutcome(Identity, Base):
    """Each later canonical outcome revision is retained separately."""

    __tablename__ = "research_forecast_outcomes"
    forecast_id: Mapped[str] = mapped_column(ForeignKey("research_forecasts.id"), index=True)
    actual_version_id: Mapped[str] = mapped_column(ForeignKey("daily_report_versions.id"))
    source_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"))
    observed: Mapped[Decimal] = mapped_column(Numeric(24, 6))
    signed_error: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    absolute_error: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    lineage: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (
        UniqueConstraint(
            "forecast_id", "actual_version_id", "source_id", name="uq_forecast_outcome_version"
        ),
        CheckConstraint("observed > 0 AND absolute_error >= 0", name="valid_outcome"),
    )
