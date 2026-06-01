from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

_sql_stats: ContextVar[SqlPerfStats | None] = ContextVar("sql_perf_stats", default=None)


@dataclass
class SqlPerfStats:
    query_count: int = 0
    sql_ms: float = 0.0

    def reset(self) -> None:
        self.query_count = 0
        self.sql_ms = 0.0


@dataclass
class TrackSearchPerf:
    count_ms: float = 0.0
    page_ids_ms: float = 0.0
    detail_ms: float = 0.0
    artists_ms: float = 0.0
    albums_ms: float = 0.0
    playlists_ms: float = 0.0
    sql_query_count: int = 0
    sql_ms: float = 0.0


_track_search_perf: ContextVar[TrackSearchPerf | None] = ContextVar(
    "track_search_perf", default=None
)


def tracks_perf_logging_enabled() -> bool:
    import os

    return os.getenv("TRACKS_PERF_LOG", "").strip() in ("1", "true", "yes")


def get_track_search_perf() -> TrackSearchPerf | None:
    return _track_search_perf.get()


def get_sql_stats() -> SqlPerfStats | None:
    return _sql_stats.get()


@contextmanager
def track_search_perf_context() -> Iterator[TrackSearchPerf]:
    perf = TrackSearchPerf()
    sql_token = _sql_stats.set(SqlPerfStats())
    perf_token = _track_search_perf.set(perf)
    try:
        yield perf
    finally:
        sql = _sql_stats.get()
        if sql is not None:
            perf.sql_query_count = sql.query_count
            perf.sql_ms = sql.sql_ms
        _track_search_perf.reset(perf_token)
        _sql_stats.reset(sql_token)


@contextmanager
def perf_segment(perf: TrackSearchPerf, field_name: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        setattr(perf, field_name, getattr(perf, field_name) + elapsed_ms)


def register_sql_perf_listeners(engine: Engine) -> None:
    if getattr(engine, "_sql_perf_registered", False):
        return

    @event.listens_for(engine, "before_cursor_execute")
    def _before(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        stats = _sql_stats.get()
        if stats is None:
            return
        conn.info.setdefault("query_start_time", []).append(time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def _after(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        stats = _sql_stats.get()
        if stats is None:
            return
        starts = conn.info.get("query_start_time")
        if not starts:
            return
        elapsed = (time.perf_counter() - starts.pop()) * 1000.0
        stats.sql_ms += elapsed
        stats.query_count += 1

    engine._sql_perf_registered = True  # type: ignore[attr-defined]
