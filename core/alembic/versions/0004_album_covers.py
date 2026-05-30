"""Album cover URL columns for UI thumbnails.

Revision ID: 0004_album_covers
Revises: 0003_perf_tracks
Create Date: 2026-05-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_album_covers"
down_revision: str | None = "0003_perf_tracks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("albums") as batch_op:
        batch_op.add_column(sa.Column("cover_image_url", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("cover_image_width", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("cover_image_height", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("albums") as batch_op:
        batch_op.drop_column("cover_image_height")
        batch_op.drop_column("cover_image_width")
        batch_op.drop_column("cover_image_url")
