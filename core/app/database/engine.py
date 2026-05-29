from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

_engine: Engine | None = None


def reset_engine() -> None:
    """Dispose cached engine (tests / DATABASE_URL changes)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def _sqlite_connect_args(database_url: str) -> dict[str, Any]:
    if not database_url.startswith("sqlite"):
        return {}
    return {"check_same_thread": False, "timeout": 30}


def _configure_sqlite_connection(dbapi_connection: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    database_url = os.getenv("DATABASE_URL", "sqlite:////app/data/spotify_curator.sqlite")
    connect_args = _sqlite_connect_args(database_url)
    _engine = create_engine(database_url, future=True, connect_args=connect_args)

    if database_url.startswith("sqlite"):

        @event.listens_for(_engine, "connect")
        def _on_connect(dbapi_connection: Any, _connection_record: Any) -> None:
            _configure_sqlite_connection(dbapi_connection)

    return _engine
