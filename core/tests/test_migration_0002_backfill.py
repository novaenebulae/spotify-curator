import json
from datetime import datetime
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


def test_migration_0002_backfills_album_id_from_raw_json(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "backfill.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()

    command.upgrade(_alembic_cfg(db_path), "0001_initial")

    engine = get_engine()
    now = datetime(2026, 5, 29, 12, 0, 0)
    album_spotify_id = "album_test_1"
    raw = {
        "id": "track_test_1",
        "name": "Test Track",
        "uri": "spotify:track:track_test_1",
        "album": {"id": album_spotify_id, "name": "Test Album", "release_date": "2020-01-01"},
    }

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO tracks (name, normalized_title, duration_ms, explicit, raw_json) "
                "VALUES ('Test Track', 'test track', 180000, 0, :raw)"
            ),
            {"raw": json.dumps(raw)},
        )
        track_id = conn.execute(text("SELECT id FROM tracks")).scalar_one()
        conn.execute(
            text(
                "INSERT INTO albums (name, normalized_name, raw_json, created_at, updated_at) "
                "VALUES ('Test Album', 'test album', '{}', :now, :now)"
            ),
            {"now": now},
        )
        album_id = conn.execute(text("SELECT id FROM albums")).scalar_one()
        conn.execute(
            text(
                "INSERT INTO spotify_albums (spotify_album_id, album_id, spotify_uri, raw_json) "
                "VALUES (:sp_album_id, :album_id, 'spotify:album:x', '{}')"
            ),
            {"sp_album_id": album_spotify_id, "album_id": album_id},
        )
        conn.execute(
            text(
                "INSERT INTO spotify_tracks "
                "(spotify_track_id, track_id, spotify_uri, market_status, raw_json) "
                "VALUES ('track_test_1', :track_id, 'spotify:track:track_test_1', 'unknown', :raw)"
            ),
            {"track_id": track_id, "raw": json.dumps(raw)},
        )

    command.upgrade(_alembic_cfg(db_path), "head")

    reset_engine()
    engine = get_engine()
    inspector = inspect(engine)
    assert "album_id" in {c["name"] for c in inspector.get_columns("spotify_tracks")}

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT album_id FROM spotify_tracks WHERE spotify_track_id = 'track_test_1'")
        ).one()
    assert row[0] == album_id
