from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.database.engine import get_engine, reset_engine

_PHASE1_HEAD_REVISION = "0001_initial"
_HEAD_REVISION = "0003_perf_tracks"
_PHASE2_REVISION = "0002_phase2_library"
_LEGACY_REVISIONS = frozenset(
    {
        "0001_baseline",
        "0002_phase15_schema",
        "0003_phase15_backfill",
    }
)

_REQUIRED_TABLES = frozenset(
    {
        "settings",
        "docker_runtime_checks",
        "oauth_pkce_states",
        "jobs",
        "tracks",
        "artists",
        "albums",
        "spotify_tracks",
        "liked_tracks",
        "playlists",
        "spotify_auth_tokens",
    }
)


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:////app/data/spotify_curator.sqlite")


def _sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    raw = database_url.removeprefix("sqlite:///")
    if raw.startswith("/"):
        return Path(raw)
    return Path(raw)


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    db_path = _sqlite_path(database_url)
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)


def _alembic_config() -> Config:
    core_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(core_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(core_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", _database_url())
    return cfg


def _current_revision(engine) -> str | None:
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        return None
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        return str(row[0]) if row else None


def _has_initial_schema(engine) -> bool:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if not _REQUIRED_TABLES.issubset(tables):
        return False
    settings_cols = {c["name"] for c in inspector.get_columns("settings")}
    jobs_cols = {c["name"] for c in inspector.get_columns("jobs")}
    return "value_json" in settings_cols and "attempt_count" in jobs_cols


def _has_phase2_schema(engine) -> bool:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "library_actions" not in tables:
        return False
    sp_cols = {c["name"] for c in inspector.get_columns("spotify_tracks")}
    return "album_id" in sp_cols


def _has_phase3_schema(engine) -> bool:
    inspector = inspect(engine)
    liked_indexes = {idx["name"] for idx in inspector.get_indexes("liked_tracks")}
    return "ix_liked_tracks_added_at" in liked_indexes


def _stamp_target_for_existing_schema(engine) -> str | None:
    if not _has_initial_schema(engine):
        return None
    if _has_phase3_schema(engine):
        return _HEAD_REVISION
    if _has_phase2_schema(engine):
        return _PHASE2_REVISION
    return _PHASE1_HEAD_REVISION


def _reconcile_legacy_revision(cfg: Config, engine) -> str | None:
    """Stamp head when DB schema matches but alembic revision is obsolete."""
    revision = _current_revision(engine)
    if revision in (_PHASE1_HEAD_REVISION, _PHASE2_REVISION, _HEAD_REVISION):
        return revision
    if revision not in _LEGACY_REVISIONS:
        return revision
    target = _stamp_target_for_existing_schema(engine)
    if target is None:
        return revision
    command.stamp(cfg, target, purge=True)
    return target


def run_migrations() -> None:
    database_url = _database_url()
    _ensure_sqlite_parent_dir(database_url)
    reset_engine()
    cfg = _alembic_config()
    engine = get_engine()

    _reconcile_legacy_revision(cfg, engine)

    try:
        command.upgrade(cfg, "head")
    except Exception as exc:
        err = str(exc).lower()
        recoverable = (
            "can't locate revision" in err
            or "already exists" in err
            or "duplicate column" in err
        )
        if recoverable and _has_initial_schema(engine):
            target = _stamp_target_for_existing_schema(engine) or _PHASE1_HEAD_REVISION
            command.stamp(cfg, target, purge=True)
            if target != _HEAD_REVISION:
                command.upgrade(cfg, "head")
        else:
            raise
