import sqlite3
from pathlib import Path

from sqlalchemy import text

from alembic import command
from app.database.engine import get_engine, reset_engine
from app.database.migrate import run_migrations


def _alembic_cfg(db_path: Path):
    from alembic.config import Config

    core_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(core_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(core_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    return cfg


def test_run_migrations_reconciles_obsolete_alembic_revision(tmp_path, monkeypatch) -> None:
    """DB at 0003_phase15_backfill with full schema must start after consolidation."""
    db_path = tmp_path / "legacy_rev.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()

    command.upgrade(_alembic_cfg(db_path), "head")

    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE alembic_version SET version_num = '0003_phase15_backfill'"
    )
    conn.commit()
    conn.close()

    reset_engine()
    run_migrations()

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    assert row is not None
    assert row[0] == "0004_album_covers"
