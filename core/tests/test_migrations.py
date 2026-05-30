from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, text

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
    assert row[0] == "0004_album_covers"

    assert "library_actions" in tables
    sp_cols = {c["name"] for c in inspector.get_columns("spotify_tracks")}
    assert "album_id" in sp_cols
    indexes = {idx["name"] for idx in inspector.get_indexes("external_ids")}
    assert "ix_external_ids_type_value" in indexes
    liked_indexes = {idx["name"] for idx in inspector.get_indexes("liked_tracks")}
    assert "ix_liked_tracks_added_at" in liked_indexes
    album_cols = {c["name"] for c in inspector.get_columns("albums")}
    assert "cover_image_url" in album_cols
