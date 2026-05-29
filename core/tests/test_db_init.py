from pathlib import Path

from sqlalchemy import inspect

from app.database.engine import get_engine
from app.database.init_db import init_db


def test_init_db_creates_settings_table(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    init_db()

    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "settings" in tables
    assert "docker_runtime_checks" in tables
    assert "oauth_pkce_states" in tables
    assert "spotify_auth_tokens" in inspector.get_table_names()
    assert "jobs" in inspector.get_table_names()
    assert "tracks" in inspector.get_table_names()
    assert "spotify_tracks" in inspector.get_table_names()
    assert "liked_tracks" in inspector.get_table_names()
    assert "playlists" in inspector.get_table_names()
    assert "playlist_tracks" in inspector.get_table_names()
    assert "snapshots" in inspector.get_table_names()
    assert "liked_track_snapshots" in inspector.get_table_names()
    assert "playlist_snapshots" in inspector.get_table_names()
    assert "playlist_track_snapshots" in inspector.get_table_names()

