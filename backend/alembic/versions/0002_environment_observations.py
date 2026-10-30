"""Add environmental observations."""

import sqlalchemy as sa
from alembic import op

revision = "0002_environment_observations"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "environment_observations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("metric", sa.String(100), nullable=False),
        sa.Column("zone", sa.String(80), nullable=False),
        sa.Column("period", sa.String(80), nullable=False),
        sa.Column("value", sa.Numeric(24, 6), nullable=True),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["daily_report_versions.id"],
            name="fk_environment_observations_version_id_daily_report_versions",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source_documents.id"],
            name="fk_environment_observations_source_id_source_documents",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_environment_observations",
        ),
        sa.UniqueConstraint(
            "version_id",
            "metric",
            "zone",
            "period",
            "unit",
            name="uq_environment_grain",
        ),
    )
    op.create_index(
        "ix_environment_observations_version_id",
        "environment_observations",
        ["version_id"],
    )


def downgrade():
    op.drop_index(
        "ix_environment_observations_version_id",
        table_name="environment_observations",
    )
    op.drop_table("environment_observations")