"""Phase 3 multi-source audio features tables.

Revision ID: 0005_phase3_features
Revises: 0004_album_covers
Create Date: 2026-05-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

from app.database.migration_bool_defaults import false, true
from app.database.migration_sql import sql_now

revision: str = "0005_phase3_features"
down_revision: str | None = "0004_album_covers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FEATURE_SOURCES_SEED = [
    ("reccobeats", "ReccoBeats", "api", "1.0.0", 40, 1, 0, 0),
    ("essentia_lowlevel", "Essentia low-level", "local", None, 60, 0, 1, 0),
    ("essentia_tensorflow", "Essentia TensorFlow", "local", None, 70, 0, 1, 0),
    ("manual", "Manual override", "manual", None, 100, 0, 0, 0),
    ("metadata", "Spotify metadata", "inferred", None, 10, 0, 0, 0),
]


def upgrade() -> None:
    op.create_table(
        "feature_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="api"),
        sa.Column("version", sa.String(length=32), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=true()),
        sa.Column("requires_audio", sa.Boolean(), nullable=False, server_default=false()),
        sa.Column("requires_api_key", sa.Boolean(), nullable=False, server_default=false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_feature_sources_name", "feature_sources", ["name"], unique=False)

    op.create_table(
        "audio_features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("feature_source_id", sa.Integer(), nullable=False),
        sa.Column("external_track_id", sa.String(length=128), nullable=True),
        sa.Column("bpm", sa.Float(), nullable=True),
        sa.Column("bpm_confidence", sa.Float(), nullable=True),
        sa.Column("energy", sa.Float(), nullable=True),
        sa.Column("energy_confidence", sa.Float(), nullable=True),
        sa.Column("danceability", sa.Float(), nullable=True),
        sa.Column("danceability_confidence", sa.Float(), nullable=True),
        sa.Column("valence", sa.Float(), nullable=True),
        sa.Column("valence_confidence", sa.Float(), nullable=True),
        sa.Column("acousticness", sa.Float(), nullable=True),
        sa.Column("acousticness_confidence", sa.Float(), nullable=True),
        sa.Column("instrumentalness", sa.Float(), nullable=True),
        sa.Column("instrumentalness_confidence", sa.Float(), nullable=True),
        sa.Column("speechiness", sa.Float(), nullable=True),
        sa.Column("speechiness_confidence", sa.Float(), nullable=True),
        sa.Column("liveness", sa.Float(), nullable=True),
        sa.Column("liveness_confidence", sa.Float(), nullable=True),
        sa.Column("loudness", sa.Float(), nullable=True),
        sa.Column("loudness_confidence", sa.Float(), nullable=True),
        sa.Column("key", sa.Integer(), nullable=True),
        sa.Column("key_confidence", sa.Float(), nullable=True),
        sa.Column("mode", sa.Integer(), nullable=True),
        sa.Column("mode_confidence", sa.Float(), nullable=True),
        sa.Column("time_signature", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("feature_confidence", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=true()),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["feature_source_id"], ["feature_sources.id"]),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audio_features_track_id", "audio_features", ["track_id"], unique=False)
    op.create_index(
        "ix_audio_features_feature_source_id", "audio_features", ["feature_source_id"], unique=False
    )
    op.create_index(
        "ix_audio_features_track_source", "audio_features", ["track_id", "feature_source_id"], unique=False
    )
    op.create_index(
        "ix_audio_features_track_source_active",
        "audio_features",
        ["track_id", "feature_source_id", "is_active"],
        unique=False,
    )
    op.create_index("ix_audio_features_status", "audio_features", ["status"], unique=False)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_audio_features_active_track_source",
            "audio_features",
            ["track_id", "feature_source_id"],
            unique=True,
            postgresql_where=sa.text("is_active = true"),
        )
    else:
        op.create_index(
            "uq_audio_features_active_track_source",
            "audio_features",
            ["track_id", "feature_source_id"],
            unique=True,
            sqlite_where=sa.text("is_active = 1"),
        )

    op.create_table(
        "audio_feature_raw_payloads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("feature_source_id", sa.Integer(), nullable=False),
        sa.Column("request_key", sa.String(length=256), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["feature_source_id"], ["feature_sources.id"]),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audio_feature_raw_payloads_track_source",
        "audio_feature_raw_payloads",
        ["track_id", "feature_source_id"],
        unique=False,
    )

    conn = op.get_bind()
    now_sql = sql_now()
    for name, display_name, source_type, version, priority, is_active, requires_audio, requires_api_key in FEATURE_SOURCES_SEED:
        if bind.dialect.name == "postgresql":
            insert_sql = f"""
                INSERT INTO feature_sources
                    (name, display_name, source_type, version, priority, is_active,
                     requires_audio, requires_api_key, created_at, updated_at)
                VALUES
                    (:name, :display_name, :source_type, :version, :priority, :is_active,
                     :requires_audio, :requires_api_key, {now_sql}, {now_sql})
                ON CONFLICT (name) DO NOTHING
                """
        else:
            insert_sql = f"""
                INSERT OR IGNORE INTO feature_sources
                    (name, display_name, source_type, version, priority, is_active,
                     requires_audio, requires_api_key, created_at, updated_at)
                VALUES
                    (:name, :display_name, :source_type, :version, :priority, :is_active,
                     :requires_audio, :requires_api_key, {now_sql}, {now_sql})
                """
        conn.execute(
            sa.text(insert_sql),
            {
                "name": name,
                "display_name": display_name,
                "source_type": source_type,
                "version": version,
                "priority": priority,
                "is_active": bool(is_active),
                "requires_audio": bool(requires_audio),
                "requires_api_key": bool(requires_api_key),
            },
        )
    conn.execute(
        sa.text(
            f"""
            UPDATE feature_sources
            SET version = '1.0.0', updated_at = {now_sql}
            WHERE name = 'reccobeats' AND (version IS NULL OR version = '')
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_audio_feature_raw_payloads_track_source", table_name="audio_feature_raw_payloads")
    op.drop_table("audio_feature_raw_payloads")
    op.drop_index("uq_audio_features_active_track_source", table_name="audio_features")
    op.drop_index("ix_audio_features_status", table_name="audio_features")
    op.drop_index("ix_audio_features_track_source_active", table_name="audio_features")
    op.drop_index("ix_audio_features_track_source", table_name="audio_features")
    op.drop_index("ix_audio_features_feature_source_id", table_name="audio_features")
    op.drop_index("ix_audio_features_track_id", table_name="audio_features")
    op.drop_table("audio_features")
    op.drop_index("ix_feature_sources_name", table_name="feature_sources")
    op.drop_table("feature_sources")
