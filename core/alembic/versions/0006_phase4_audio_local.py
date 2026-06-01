"""Phase 4 local audio: job_items, workers, track_segments, analysis jobs.

Revision ID: 0006_phase4_audio_local
Revises: 0005_phase3_features
Create Date: 2026-06-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_phase4_audio_local"
down_revision: str | None = "0005_phase3_features"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("segment_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("input_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_items_job_id", "job_items", ["job_id"], unique=False)
    op.create_index("ix_job_items_item_type", "job_items", ["item_type"], unique=False)
    op.create_index("ix_job_items_status", "job_items", ["status"], unique=False)
    op.create_index("ix_job_items_track_id", "job_items", ["track_id"], unique=False)
    op.create_index("ix_job_items_segment_id", "job_items", ["segment_id"], unique=False)
    op.create_index("ix_job_items_locked_by", "job_items", ["locked_by"], unique=False)
    op.create_index("ix_job_items_job_status", "job_items", ["job_id", "status"], unique=False)
    op.create_index(
        "ix_job_items_available",
        "job_items",
        ["status", "next_retry_at", "priority"],
        unique=False,
    )

    op.create_table(
        "worker_heartbeats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("worker_id", sa.String(length=128), nullable=False),
        sa.Column("worker_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="starting"),
        sa.Column("current_job_id", sa.String(length=64), nullable=True),
        sa.Column("current_item_id", sa.String(length=64), nullable=True),
        sa.Column("hostname", sa.String(length=256), nullable=True),
        sa.Column("process_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["current_job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_id"),
    )
    op.create_index("ix_worker_heartbeats_worker_type", "worker_heartbeats", ["worker_type"])
    op.create_index("ix_worker_heartbeats_last_seen_at", "worker_heartbeats", ["last_seen_at"])

    op.create_table(
        "job_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=True),
        sa.Column("level", sa.String(length=16), nullable=False, server_default="info"),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("context_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_events_job_id", "job_events", ["job_id"])
    op.create_index("ix_job_events_item_id", "job_events", ["item_id"])
    op.create_index("ix_job_events_event_type", "job_events", ["event_type"])
    op.create_index("ix_job_events_job_created", "job_events", ["job_id", "created_at"])

    op.create_table(
        "audio_download_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="ytdlp"),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("rate_limited", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audio_download_jobs_job_id", "audio_download_jobs", ["job_id"])
    op.create_index("ix_audio_download_jobs_track_id", "audio_download_jobs", ["track_id"])
    op.create_index("ix_audio_download_jobs_status", "audio_download_jobs", ["status"])

    op.create_table(
        "track_segments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("analysis_job_id", sa.Integer(), nullable=True),
        sa.Column("download_job_id", sa.Integer(), nullable=True),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("segment_type", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="youtube"),
        sa.Column("source_url_hash", sa.String(length=64), nullable=True),
        sa.Column("temporary_path", sa.Text(), nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("features_json", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("duration_seconds <= 30", name="ck_track_segments_duration_max_30"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.ForeignKeyConstraint(["download_job_id"], ["audio_download_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_track_segments_track_id", "track_segments", ["track_id"])
    op.create_index("ix_track_segments_source_url_hash", "track_segments", ["source_url_hash"])
    op.create_index(
        "ix_track_segments_track_deleted",
        "track_segments",
        ["track_id", "deleted_at"],
    )

    op.create_table(
        "audio_analysis_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("segment_id", sa.Integer(), nullable=True),
        sa.Column("analysis_level", sa.String(length=64), nullable=False),
        sa.Column("docker_service", sa.String(length=64), nullable=True),
        sa.Column("image_name", sa.String(length=256), nullable=True),
        sa.Column("image_tag", sa.String(length=64), nullable=True),
        sa.Column("pipeline_version", sa.String(length=64), nullable=True),
        sa.Column("input_path", sa.Text(), nullable=True),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.ForeignKeyConstraint(["segment_id"], ["track_segments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audio_analysis_jobs_job_id", "audio_analysis_jobs", ["job_id"])
    op.create_index("ix_audio_analysis_jobs_track_id", "audio_analysis_jobs", ["track_id"])
    op.create_index("ix_audio_analysis_jobs_segment_id", "audio_analysis_jobs", ["segment_id"])
    op.create_index("ix_audio_analysis_jobs_status", "audio_analysis_jobs", ["status"])
    op.create_index(
        "ix_audio_analysis_jobs_analysis_level",
        "audio_analysis_jobs",
        ["analysis_level"],
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE feature_sources
            SET is_active = 1, requires_audio = 1, updated_at = datetime('now')
            WHERE name = 'essentia_lowlevel'
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_audio_analysis_jobs_analysis_level", table_name="audio_analysis_jobs")
    op.drop_index("ix_audio_analysis_jobs_status", table_name="audio_analysis_jobs")
    op.drop_index("ix_audio_analysis_jobs_segment_id", table_name="audio_analysis_jobs")
    op.drop_index("ix_audio_analysis_jobs_track_id", table_name="audio_analysis_jobs")
    op.drop_index("ix_audio_analysis_jobs_job_id", table_name="audio_analysis_jobs")
    op.drop_table("audio_analysis_jobs")

    op.drop_index("ix_track_segments_track_deleted", table_name="track_segments")
    op.drop_index("ix_track_segments_source_url_hash", table_name="track_segments")
    op.drop_index("ix_track_segments_track_id", table_name="track_segments")
    op.drop_table("track_segments")

    op.drop_index("ix_audio_download_jobs_status", table_name="audio_download_jobs")
    op.drop_index("ix_audio_download_jobs_track_id", table_name="audio_download_jobs")
    op.drop_index("ix_audio_download_jobs_job_id", table_name="audio_download_jobs")
    op.drop_table("audio_download_jobs")

    op.drop_index("ix_job_events_job_created", table_name="job_events")
    op.drop_index("ix_job_events_event_type", table_name="job_events")
    op.drop_index("ix_job_events_item_id", table_name="job_events")
    op.drop_index("ix_job_events_job_id", table_name="job_events")
    op.drop_table("job_events")

    op.drop_index("ix_worker_heartbeats_last_seen_at", table_name="worker_heartbeats")
    op.drop_index("ix_worker_heartbeats_worker_type", table_name="worker_heartbeats")
    op.drop_table("worker_heartbeats")

    op.drop_index("ix_job_items_available", table_name="job_items")
    op.drop_index("ix_job_items_job_status", table_name="job_items")
    op.drop_index("ix_job_items_locked_by", table_name="job_items")
    op.drop_index("ix_job_items_segment_id", table_name="job_items")
    op.drop_index("ix_job_items_track_id", table_name="job_items")
    op.drop_index("ix_job_items_status", table_name="job_items")
    op.drop_index("ix_job_items_item_type", table_name="job_items")
    op.drop_index("ix_job_items_job_id", table_name="job_items")
    op.drop_table("job_items")

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE feature_sources
            SET is_active = 0, updated_at = datetime('now')
            WHERE name = 'essentia_lowlevel'
            """
        )
    )
