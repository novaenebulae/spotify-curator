"""Dialect-specific SQL fragments for Alembic data migrations."""

from __future__ import annotations

from alembic import op


def sql_now() -> str:
    if op.get_bind().dialect.name == "postgresql":
        return "NOW()"
    return "datetime('now')"
