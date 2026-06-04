"""Phase 6 track_embeddings table.

Revision ID: 0011_phase6_track_embeddings
Revises: 0010_phase6_track_advanced_features
Create Date: 2026-06-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_phase6_track_embeddings"
down_revision: str | None = "0010_phase6_track_advanced_features"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "track_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("model_hash", sa.String(length=128), nullable=True),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("vector_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("aggregation_method", sa.String(length=32), nullable=True),
        sa.Column("segments_used", sa.Integer(), nullable=True),
        sa.Column("pipeline_version", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "track_id",
            "source",
            "model_name",
            "pipeline_version",
            name="uq_track_embeddings_track_source_model",
        ),
    )
    op.create_index("ix_track_embeddings_track_id", "track_embeddings", ["track_id"], unique=False)
    op.create_index("ix_track_embeddings_source", "track_embeddings", ["source"], unique=False)
    op.create_index("ix_track_embeddings_status", "track_embeddings", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_track_embeddings_status", table_name="track_embeddings")
    op.drop_index("ix_track_embeddings_source", table_name="track_embeddings")
    op.drop_index("ix_track_embeddings_track_id", table_name="track_embeddings")
    op.drop_table("track_embeddings")
