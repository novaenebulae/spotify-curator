"""Add match_strategy to track_previews.

Revision ID: 0012_track_previews_match_strategy
Revises: 0011_phase6_track_embeddings
Create Date: 2026-06-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_track_previews_match_strategy"
down_revision: str | None = "0011_phase6_track_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "track_previews",
        sa.Column("match_strategy", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("track_previews", "match_strategy")
