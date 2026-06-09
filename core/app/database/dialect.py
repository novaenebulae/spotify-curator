from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database.url import resolve_database_url


def database_url() -> str:
    return resolve_database_url()


def is_sqlite_database() -> bool:
    return database_url().startswith("sqlite")


def is_postgresql_database() -> bool:
    url = database_url()
    return url.startswith("postgresql") or url.startswith("postgres")


def begin_exclusive_write(conn: Connection) -> None:
    """SQLite needs BEGIN IMMEDIATE for worker reservation; Postgres uses row locks."""
    if is_sqlite_database():
        conn.execute(text("BEGIN IMMEDIATE"))
