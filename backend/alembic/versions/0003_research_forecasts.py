"""Separate prospective research issues and versioned outcome comparisons."""

import sqlalchemy as sa
from alembic import op

revision = "0003_research_forecasts"
down_revision = "0002_environment_observations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "research_forecasts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("model_id", sa.String(64), nullable=False),
        sa.Column("model_experiment_id", sa.String(64), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("prediction", sa.Numeric(24, 9), nullable=True),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "model_id", "target_date", "input_fingerprint", name="uq_research_forecast_input"
        ),
        sa.CheckConstraint(
            "status IN ('forecast','withheld')", name=op.f("ck_research_forecasts_status")
        ),
        sa.CheckConstraint(
            "(status = 'forecast' AND prediction IS NOT NULL AND prediction > 0) OR "
            "(status = 'withheld' AND prediction IS NULL)",
            name=op.f("ck_research_forecasts_prediction_state"),
        ),
        sa.CheckConstraint(
            "length(id) = 64 AND length(model_id) = 64 AND length(input_fingerprint) = 64",
            name=op.f("ck_research_forecasts_fingerprints"),
        ),
    )
    op.create_index("ix_research_forecasts_model_id", "research_forecasts", ["model_id"])
    op.create_index("ix_research_forecasts_target_date", "research_forecasts", ["target_date"])
    op.create_table(
        "research_forecast_outcomes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "forecast_id", sa.String(64), sa.ForeignKey("research_forecasts.id"), nullable=False
        ),
        sa.Column(
            "actual_version_id",
            sa.String(36),
            sa.ForeignKey("daily_report_versions.id"),
            nullable=False,
        ),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("source_documents.id"), nullable=False),
        sa.Column("observed", sa.Numeric(24, 6), nullable=False),
        sa.Column("signed_error", sa.Numeric(24, 9), nullable=False),
        sa.Column("absolute_error", sa.Numeric(24, 9), nullable=False),
        sa.Column("lineage", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "forecast_id", "actual_version_id", "source_id", name="uq_forecast_outcome_version"
        ),
        sa.CheckConstraint(
            "observed > 0 AND absolute_error >= 0",
            name=op.f("ck_research_forecast_outcomes_valid_outcome"),
        ),
    )
    op.create_index(
        "ix_research_forecast_outcomes_forecast_id", "research_forecast_outcomes", ["forecast_id"]
    )


def downgrade():
    op.drop_table("research_forecast_outcomes")
    op.drop_table("research_forecasts")
