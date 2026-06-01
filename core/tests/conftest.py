import os
import sys
from pathlib import Path

import pytest

CORE_ROOT = Path(__file__).resolve().parents[1]

if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

os.environ.setdefault("PYTHONPATH", str(CORE_ROOT))


@pytest.fixture(autouse=True)
def _reset_sqlite_engine() -> None:
    from app.database.engine import reset_engine

    reset_engine()
    yield
    reset_engine()


@pytest.fixture
def audio_db(tmp_path, monkeypatch):
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from alembic import command
    from app.database.engine import reset_engine

    db_path = tmp_path / "audio_test.sqlite"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("CACHE_DIR", str(cache_dir))
    reset_engine()
    core_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(core_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(core_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                INSERT INTO tracks (id, name, normalized_title, duration_ms, created_at, updated_at)
                VALUES (1, 'Test Song', 'test song', 180000, datetime('now'), datetime('now'))
                """
            )
        )
        conn.commit()
    yield engine
    reset_engine()
