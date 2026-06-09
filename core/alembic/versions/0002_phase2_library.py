"""Phase 2 library schema: library_actions, album_id, search indexes.

Revision ID: 0002_phase2_library
Revises: 0001_initial
Create Date: 2026-05-29

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

from app.database.migration_bool_defaults import false, true

revision: str = "0002_phase2_library"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "library_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="previewed"),
        sa.Column("filter_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("selected_track_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("affected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=true()),
        sa.Column("spotify_applied", sa.Boolean(), nullable=False, server_default=false()),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("warning_json", sa.Text(), nullable=True),
        sa.Column("created_by_context", sa.String(length=32), nullable=False, server_default="api"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_library_actions_action_type", "library_actions", ["action_type"])
    op.create_index("ix_library_actions_status", "library_actions", ["status"])
    op.create_index("ix_library_actions_dry_run", "library_actions", ["dry_run"])

    with op.batch_alter_table("spotify_tracks") as batch_op:
        batch_op.add_column(sa.Column("album_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_spotify_tracks_album_id",
            "albums",
            ["album_id"],
            ["id"],
        )
    op.create_index("ix_spotify_tracks_album_id", "spotify_tracks", ["album_id"])

    op.create_index(
        "ix_external_ids_type_value",
        "external_ids",
        ["id_type", "id_value"],
    )
    op.create_index(
        "ix_liked_tracks_is_current_added_at",
        "liked_tracks",
        ["is_current", "added_at"],
    )
    op.create_index(
        "ix_playlist_tracks_track_current",
        "playlist_tracks",
        ["spotify_track_id", "is_current"],
    )
    op.create_index("ix_tracks_duration_ms", "tracks", ["duration_ms"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            UPDATE spotify_tracks AS st
            SET album_id = sa.album_id
            FROM spotify_albums AS sa
            WHERE sa.spotify_album_id = (st.raw_json::json->'album'->>'id')
              AND (st.raw_json::json->'album'->>'id') IS NOT NULL
            """
        )
    else:
        op.execute(
            """
            UPDATE spotify_tracks
            SET album_id = (
                SELECT sa.album_id
                FROM spotify_albums sa
                WHERE sa.spotify_album_id = json_extract(spotify_tracks.raw_json, '$.album.id')
            )
            WHERE json_extract(spotify_tracks.raw_json, '$.album.id') IS NOT NULL
            """
        )


def downgrade() -> None:
    op.drop_index("ix_tracks_duration_ms", table_name="tracks")
    op.drop_index("ix_playlist_tracks_track_current", table_name="playlist_tracks")
    op.drop_index("ix_liked_tracks_is_current_added_at", table_name="liked_tracks")
    op.drop_index("ix_external_ids_type_value", table_name="external_ids")
    op.drop_index("ix_spotify_tracks_album_id", table_name="spotify_tracks")
    with op.batch_alter_table("spotify_tracks") as batch_op:
        batch_op.drop_constraint("fk_spotify_tracks_album_id", type_="foreignkey")
        batch_op.drop_column("album_id")
    op.drop_index("ix_library_actions_dry_run", table_name="library_actions")
    op.drop_index("ix_library_actions_status", table_name="library_actions")
    op.drop_index("ix_library_actions_action_type", table_name="library_actions")
    op.drop_table("library_actions")
