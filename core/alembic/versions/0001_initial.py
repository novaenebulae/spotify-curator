"""Initial schema (phase 1.5 consolidated).

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-29

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

from app.database.migration_bool_defaults import false, true

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("key", sa.String(length=200), nullable=False, unique=True),
        sa.Column("value_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "docker_runtime_checks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("check_name", sa.String(length=128), nullable=False),
        sa.Column("service_name", sa.String(length=128), nullable=True),
        sa.Column("image_name", sa.String(length=256), nullable=True),
        sa.Column("image_tag", sa.String(length=128), nullable=True),
        sa.Column("command", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "oauth_pkce_states",
        sa.Column("state", sa.String(length=128), primary_key=True),
        sa.Column("code_verifier", sa.String(length=256), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_step", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("result_json", sa.String(length=100000), nullable=False, server_default="{}"),
        sa.Column("last_error", sa.String(length=100000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("normalized_title", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("explicit", sa.Boolean(), nullable=False, server_default=false()),
        sa.Column("popularity", sa.Integer(), nullable=True),
        sa.Column("preview_url", sa.String(length=2000), nullable=True),
        sa.Column("external_url", sa.String(length=2000), nullable=True),
        sa.Column("raw_json", sa.String(length=100000), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_tracks_normalized_title", "tracks", ["normalized_title"])

    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("normalized_name", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("raw_json", sa.String(length=100000), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_artists_normalized_name", "artists", ["normalized_name"])

    op.create_table(
        "albums",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("normalized_name", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("release_date", sa.String(length=32), nullable=True),
        sa.Column("raw_json", sa.String(length=100000), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_albums_normalized_name", "albums", ["normalized_name"])

    op.create_table(
        "track_artists",
        sa.Column("track_id", sa.Integer(), sa.ForeignKey("tracks.id"), primary_key=True),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id"), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "spotify_tracks",
        sa.Column("spotify_track_id", sa.String(length=64), primary_key=True),
        sa.Column("track_id", sa.Integer(), sa.ForeignKey("tracks.id"), nullable=False, unique=True),
        sa.Column("spotify_uri", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("is_playable", sa.Boolean(), nullable=True),
        sa.Column(
            "available_markets_json",
            sa.String(length=100000),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("linked_from_spotify_track_id", sa.String(length=64), nullable=True),
        sa.Column(
            "restrictions_json",
            sa.String(length=100000),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("market_status", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("raw_json", sa.String(length=100000), nullable=False, server_default="{}"),
    )
    op.create_index("ix_spotify_tracks_market_status", "spotify_tracks", ["market_status"])

    op.create_table(
        "spotify_artists",
        sa.Column("spotify_artist_id", sa.String(length=64), primary_key=True),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id"), nullable=False, unique=True),
        sa.Column("spotify_uri", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("raw_json", sa.String(length=100000), nullable=False, server_default="{}"),
    )
    op.create_table(
        "spotify_albums",
        sa.Column("spotify_album_id", sa.String(length=64), primary_key=True),
        sa.Column("album_id", sa.Integer(), sa.ForeignKey("albums.id"), nullable=False, unique=True),
        sa.Column("spotify_uri", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("raw_json", sa.String(length=100000), nullable=False, server_default="{}"),
    )
    op.create_table(
        "external_ids",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("track_id", sa.Integer(), sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("id_type", sa.String(length=64), nullable=False),
        sa.Column("id_value", sa.String(length=256), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="spotify"),
        sa.Column("external_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.UniqueConstraint("track_id", "id_type", name="uq_external_ids_track_type"),
    )
    op.create_table(
        "liked_tracks",
        sa.Column(
            "spotify_track_id",
            sa.String(length=64),
            sa.ForeignKey("spotify_tracks.spotify_track_id"),
            primary_key=True,
        ),
        sa.Column("added_at", sa.DateTime(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=true()),
        sa.Column("first_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("raw_json", sa.String(length=100000), nullable=False, server_default="{}"),
    )
    op.create_index("ix_liked_tracks_is_current", "liked_tracks", ["is_current"])

    op.create_table(
        "playlists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("spotify_playlist_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("spotify_uri", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("name", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("description", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("owner_spotify_user_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("is_public", sa.Boolean(), nullable=True),
        sa.Column("collaborative", sa.Boolean(), nullable=True),
        sa.Column("spotify_snapshot_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("raw_json", sa.String(length=100000), nullable=False, server_default="{}"),
        sa.Column("first_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "playlist_tracks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "spotify_playlist_id",
            sa.String(length=64),
            sa.ForeignKey("playlists.spotify_playlist_id"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "spotify_track_id",
            sa.String(length=64),
            sa.ForeignKey("spotify_tracks.spotify_track_id"),
            nullable=True,
        ),
        sa.Column("added_at", sa.DateTime(), nullable=True),
        sa.Column(
            "added_by_spotify_user_id",
            sa.String(length=128),
            nullable=False,
            server_default="",
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=true()),
        sa.Column("is_local", sa.Boolean(), nullable=False, server_default=false()),
        sa.Column("null_reason", sa.String(length=64), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("raw_json", sa.String(length=100000), nullable=False, server_default="{}"),
        sa.UniqueConstraint(
            "spotify_playlist_id",
            "position",
            name="uq_playlist_tracks_playlist_position",
        ),
    )
    op.create_index("ix_playlist_tracks_spotify_playlist_id", "playlist_tracks", ["spotify_playlist_id"])
    op.create_index("ix_playlist_tracks_is_current", "playlist_tracks", ["is_current"])

    op.create_table(
        "snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("snapshot_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("track_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("playlist_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.String(length=100000), nullable=False, server_default="{}"),
    )
    op.create_table(
        "liked_track_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.String(length=64), sa.ForeignKey("snapshots.id"), nullable=False),
        sa.Column(
            "spotify_track_id",
            sa.String(length=64),
            sa.ForeignKey("spotify_tracks.spotify_track_id"),
            nullable=False,
        ),
        sa.Column("added_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("snapshot_id", "spotify_track_id", name="uq_liked_track_snapshots"),
    )
    op.create_table(
        "playlist_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.String(length=64), sa.ForeignKey("snapshots.id"), nullable=False),
        sa.Column(
            "spotify_playlist_id",
            sa.String(length=64),
            sa.ForeignKey("playlists.spotify_playlist_id"),
            nullable=False,
        ),
        sa.Column("spotify_snapshot_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("snapshot_id", "spotify_playlist_id", name="uq_playlist_snapshots"),
    )
    op.create_table(
        "playlist_track_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.String(length=64), sa.ForeignKey("snapshots.id"), nullable=False),
        sa.Column("spotify_playlist_id", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("spotify_track_id", sa.String(length=64), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "snapshot_id",
            "spotify_playlist_id",
            "position",
            name="uq_playlist_track_snapshots_position",
        ),
    )
    op.create_table(
        "spotify_auth_tokens",
        sa.Column("user_id", sa.String(length=128), primary_key=True),
        sa.Column("access_token", sa.String(length=2048), nullable=False),
        sa.Column("refresh_token", sa.String(length=2048), nullable=True),
        sa.Column("token_type", sa.String(length=32), nullable=False, server_default="Bearer"),
        sa.Column("scope", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("raw_json", sa.String(length=100000), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("spotify_auth_tokens")
    op.drop_table("playlist_track_snapshots")
    op.drop_table("playlist_snapshots")
    op.drop_table("liked_track_snapshots")
    op.drop_table("snapshots")
    op.drop_index("ix_playlist_tracks_is_current", table_name="playlist_tracks")
    op.drop_index("ix_playlist_tracks_spotify_playlist_id", table_name="playlist_tracks")
    op.drop_table("playlist_tracks")
    op.drop_table("playlists")
    op.drop_index("ix_liked_tracks_is_current", table_name="liked_tracks")
    op.drop_table("liked_tracks")
    op.drop_table("external_ids")
    op.drop_table("spotify_albums")
    op.drop_table("spotify_artists")
    op.drop_index("ix_spotify_tracks_market_status", table_name="spotify_tracks")
    op.drop_table("spotify_tracks")
    op.drop_table("track_artists")
    op.drop_index("ix_albums_normalized_name", table_name="albums")
    op.drop_table("albums")
    op.drop_index("ix_artists_normalized_name", table_name="artists")
    op.drop_table("artists")
    op.drop_index("ix_tracks_normalized_title", table_name="tracks")
    op.drop_table("tracks")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_job_type", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("oauth_pkce_states")
    op.drop_table("docker_runtime_checks")
    op.drop_table("settings")
