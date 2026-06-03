from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from app.database.url import resolve_database_url

_engine: Engine | None = None

_ALLOWED_JOURNAL_MODES = frozenset({"WAL", "DELETE", "TRUNCATE", "PERSIST", "MEMORY"})


def reset_engine() -> None:
    """Dispose cached engine (tests / DATABASE_URL changes)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def _sqlite_journal_mode() -> str:
    mode = os.getenv("SQLITE_JOURNAL_MODE", "WAL").strip().upper()
    if mode not in _ALLOWED_JOURNAL_MODES:
        return "WAL"
    return mode


def _sqlite_connect_args(database_url: str) -> dict[str, Any]:
    if not database_url.startswith("sqlite"):
        return {}
    return {"check_same_thread": False, "timeout": 30}


def _configure_sqlite_connection(dbapi_connection: Any) -> None:
    journal_mode = _sqlite_journal_mode()
    cursor = dbapi_connection.cursor()
    cursor.execute(f"PRAGMA journal_mode={journal_mode}")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    database_url = resolve_database_url()
    connect_args = _sqlite_connect_args(database_url)
    _engine = create_engine(database_url, future=True, connect_args=connect_args)

    from app.observability.sql_perf import register_sql_perf_listeners

    register_sql_perf_listeners(_engine)

    if database_url.startswith("sqlite"):

        @event.listens_for(_engine, "connect")
        def _on_connect(dbapi_connection: Any, _connection_record: Any) -> None:
            _configure_sqlite_connection(dbapi_connection)

    return _engine
