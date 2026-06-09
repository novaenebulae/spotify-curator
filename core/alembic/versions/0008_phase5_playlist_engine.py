"""Phase 5 playlist engine tables.

Revision ID: 0008_phase5_playlist_engine
Revises: 0007_track_previews_hybrid
Create Date: 2026-06-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

from app.database.migration_bool_defaults import true

revision: str = "0008_phase5_playlist_engine"
down_revision: str | None = "0007_track_previews_hybrid"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "playlist_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_json", sa.Text(), nullable=False),
        sa.Column("rule_yaml", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playlist_rules_name", "playlist_rules", ["name"])
    op.create_index("ix_playlist_rules_enabled", "playlist_rules", ["enabled"])

    op.create_table(
        "generated_playlists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("playlist_rule_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="previewed"),
        sa.Column("target_size", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("actual_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engine_version", sa.String(length=64), nullable=False, server_default="playlist_engine_v1"),
        sa.Column("score_summary_json", sa.Text(), nullable=True),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("warning_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["playlist_rule_id"], ["playlist_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_playlists_playlist_rule_id", "generated_playlists", ["playlist_rule_id"])
    op.create_index("ix_generated_playlists_status", "generated_playlists", ["status"])

    op.create_table(
        "generated_playlist_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("generated_playlist_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_details_json", sa.Text(), nullable=False),
        sa.Column("selected_reason", sa.Text(), nullable=True),
        sa.Column("exclusion_details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["generated_playlist_id"], ["generated_playlists.id"]),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generated_playlist_items_generated_playlist_id",
        "generated_playlist_items",
        ["generated_playlist_id"],
    )
    op.create_index("ix_generated_playlist_items_track_id", "generated_playlist_items", ["track_id"])
    op.create_index(
        "ix_generated_playlist_items_gp_track",
        "generated_playlist_items",
        ["generated_playlist_id", "track_id"],
    )

    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("generated_playlist_id", sa.Integer(), nullable=False),
        sa.Column("target_spotify_playlist_id", sa.String(length=64), nullable=True),
        sa.Column("sync_mode", sa.String(length=32), nullable=False, server_default="replace"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=true()),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="previewed"),
        sa.Column("diff_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["generated_playlist_id"], ["generated_playlists.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_jobs_generated_playlist_id", "sync_jobs", ["generated_playlist_id"])
    op.create_index("ix_sync_jobs_status", "sync_jobs", ["status"])
    op.create_index("ix_sync_jobs_job_id", "sync_jobs", ["job_id"])

    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sync_job_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False, server_default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["sync_job_id"], ["sync_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_logs_sync_job_id", "sync_logs", ["sync_job_id"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")
        )


def downgrade() -> None:
    op.drop_table("sync_logs")
    op.drop_table("sync_jobs")
    op.drop_table("generated_playlist_items")
    op.drop_table("generated_playlists")
    op.drop_table("playlist_rules")
