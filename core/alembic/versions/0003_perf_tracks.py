"""Performance indexes for track list queries.

Revision ID: 0003_perf_tracks
Revises: 0002_phase2_library
Create Date: 2026-05-29

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_perf_tracks"
down_revision: str | None = "0002_phase2_library"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_liked_tracks_added_at", "liked_tracks", ["added_at"])
    op.create_index("ix_track_artists_track_position", "track_artists", ["track_id", "position"])


def downgrade() -> None:
    op.drop_index("ix_track_artists_track_position", table_name="track_artists")
    op.drop_index("ix_liked_tracks_added_at", table_name="liked_tracks")
