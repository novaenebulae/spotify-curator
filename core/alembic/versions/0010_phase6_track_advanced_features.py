"""Phase 6 track_advanced_features table.

Revision ID: 0010_phase6_track_advanced_features
Revises: 0009_phase6_job_items_pipeline_stages
Create Date: 2026-06-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_phase6_track_advanced_features"
down_revision: str | None = "0009_phase6_job_items_pipeline_stages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "track_advanced_features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("feature_name", sa.String(length=64), nullable=False),
        sa.Column("value_float", sa.Float(), nullable=True),
        sa.Column("value_text", sa.String(length=512), nullable=True),
        sa.Column("value_json", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("model_hash", sa.String(length=128), nullable=True),
        sa.Column("pipeline_version", sa.String(length=64), nullable=True),
        sa.Column("aggregation_method", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "track_id",
            "feature_name",
            "source",
            "model_name",
            "pipeline_version",
            name="uq_track_advanced_features_track_feature_source",
        ),
    )
    op.create_index(
        "ix_track_advanced_features_track_id",
        "track_advanced_features",
        ["track_id"],
        unique=False,
    )
    op.create_index(
        "ix_track_advanced_features_feature_name",
        "track_advanced_features",
        ["feature_name"],
        unique=False,
    )
    op.create_index(
        "ix_track_advanced_features_source",
        "track_advanced_features",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_track_advanced_features_status",
        "track_advanced_features",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_track_advanced_features_track_feature",
        "track_advanced_features",
        ["track_id", "feature_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_track_advanced_features_track_feature",
        table_name="track_advanced_features",
    )
    op.drop_index("ix_track_advanced_features_status", table_name="track_advanced_features")
    op.drop_index("ix_track_advanced_features_source", table_name="track_advanced_features")
    op.drop_index(
        "ix_track_advanced_features_feature_name",
        table_name="track_advanced_features",
    )
    op.drop_index("ix_track_advanced_features_track_id", table_name="track_advanced_features")
    op.drop_table("track_advanced_features")
