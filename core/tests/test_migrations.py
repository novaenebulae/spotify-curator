from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.database.engine import get_engine, reset_engine


def _alembic_cfg(db_path: Path) -> Config:
    core_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(core_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(core_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    return cfg


def test_migrations_upgrade_head_on_empty_db(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "migrations.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()

    command.upgrade(_alembic_cfg(db_path), "head")

    engine = get_engine()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "liked_tracks" in tables
    assert "docker_runtime_checks" in tables
    assert "oauth_pkce_states" in tables

    liked_cols = {c["name"] for c in inspector.get_columns("liked_tracks")}
    assert "is_current" in liked_cols
    assert "first_seen_at" in liked_cols

    jobs_cols = {c["name"] for c in inspector.get_columns("jobs")}
    assert "attempt_count" in jobs_cols

    settings_cols = {c["name"] for c in inspector.get_columns("settings")}
    assert "value_json" in settings_cols

    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    assert row is not None
    assert row[0] == "0008_phase5_playlist_engine"

    assert "library_actions" in tables
    sp_cols = {c["name"] for c in inspector.get_columns("spotify_tracks")}
    assert "album_id" in sp_cols
    indexes = {idx["name"] for idx in inspector.get_indexes("external_ids")}
    assert "ix_external_ids_type_value" in indexes
    liked_indexes = {idx["name"] for idx in inspector.get_indexes("liked_tracks")}
    assert "ix_liked_tracks_added_at" in liked_indexes
    album_cols = {c["name"] for c in inspector.get_columns("albums")}
    assert "cover_image_url" in album_cols

    assert "feature_sources" in tables
    assert "audio_features" in tables
    assert "audio_feature_raw_payloads" in tables

    af_cols = {c["name"] for c in inspector.get_columns("audio_features")}
    assert "bpm" in af_cols
    assert "feature_source_id" in af_cols
    assert "status" in af_cols

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM feature_sources")).scalar()
    assert count == 5

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT name, is_active FROM feature_sources WHERE name = 'reccobeats'")
        ).fetchone()
    assert row is not None
    assert row[0] == "reccobeats"
    assert row[1] == 1

    assert "track_previews" in tables
    tp_cols = {c["name"] for c in inspector.get_columns("track_previews")}
    assert "preview_url" in tp_cols
    assert "match_confidence" in tp_cols

    seg_cols = {c["name"] for c in inspector.get_columns("track_segments")}
    assert "source_quality" in seg_cols

    assert "job_items" in tables
    assert "track_segments" in tables
    assert "worker_heartbeats" in tables

    assert "playlist_rules" in tables
    assert "generated_playlists" in tables
    assert "generated_playlist_items" in tables
    assert "sync_jobs" in tables
    assert "sync_logs" in tables
    gp_cols = {c["name"] for c in inspector.get_columns("generated_playlists")}
    assert "engine_version" in gp_cols
    assert "warning_json" in gp_cols
    gpi_cols = {c["name"] for c in inspector.get_columns("generated_playlist_items")}
    assert "exclusion_details_json" in gpi_cols

    with engine.connect() as conn:
        ess = conn.execute(
            text("SELECT is_active FROM feature_sources WHERE name = 'essentia_lowlevel'")
        ).fetchone()
    assert ess is not None
    assert ess[0] == 1

    with engine.connect() as conn:
        conn.execute(
            text(
                """
                INSERT INTO tracks (id, name, normalized_title, duration_ms, created_at, updated_at)
                VALUES (1, 't', 't', 60000, datetime('now'), datetime('now'))
                """
            )
        )
        conn.commit()
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    """
                    INSERT INTO track_segments
                    (track_id, start_seconds, end_seconds, duration_seconds, segment_type, source, created_at)
                    VALUES (1, 0, 35, 35, 'A', 'test', datetime('now'))
                    """
                )
            )
            conn.commit()
