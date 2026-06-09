"""Cross-dialect boolean server defaults for Alembic migrations."""

from __future__ import annotations

import sqlalchemy as sa


def false() -> sa.False_:
    return sa.false()


def true() -> sa.True_:
    return sa.true()
