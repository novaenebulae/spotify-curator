"""Phase 4.1 track_previews + hybrid segment metadata.

Revision ID: 0007_track_previews_hybrid
Revises: 0006_phase4_audio_local
Create Date: 2026-06-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_track_previews_hybrid"
down_revision: str | None = "0006_phase4_audio_local"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "track_previews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_track_id", sa.String(length=64), nullable=True),
        sa.Column("provider_url", sa.Text(), nullable=True),
        sa.Column("preview_url", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("format", sa.String(length=32), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("artist", sa.String(length=500), nullable=True),
        sa.Column("album", sa.String(length=500), nullable=True),
        sa.Column("isrc", sa.String(length=32), nullable=True),
        sa.Column("provider_duration_seconds", sa.Float(), nullable=True),
        sa.Column("expected_duration_seconds", sa.Float(), nullable=True),
        sa.Column("duration_delta_seconds", sa.Float(), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("match_confidence", sa.Float(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("track_id", "provider", name="uq_track_previews_track_provider"),
    )
    op.create_index("ix_track_previews_track_id", "track_previews", ["track_id"])
    op.create_index(
        "ix_track_previews_provider_available",
        "track_previews",
        ["provider", "is_available"],
    )

    with op.batch_alter_table("track_segments") as batch_op:
        batch_op.add_column(sa.Column("source_quality", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("track_segments") as batch_op:
        batch_op.drop_column("source_quality")

    op.drop_index("ix_track_previews_provider_available", table_name="track_previews")
    op.drop_index("ix_track_previews_track_id", table_name="track_previews")
    op.drop_table("track_previews")
