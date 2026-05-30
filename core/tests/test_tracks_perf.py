from __future__ import annotations

import time

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.repositories.tracks import TracksRepository
from app.library.schemas import TrackSearchFilters
from app.library.search import TrackSearchService
from app.main import create_app
from app.observability.sql_perf import _sql_stats, track_search_perf_context
from tests.fixtures.library_seed import seed_library
from tests.fixtures.library_seed_large import seed_large_library


def _client(tmp_path, monkeypatch, *, large: bool = False) -> TestClient:
    db_path = tmp_path / ("tracks_perf_large.sqlite" if large else "tracks_perf.sqlite")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        if large:
            seed_large_library(session, track_count=5000)
        else:
            seed_library(session)
    return TestClient(create_app())


def test_list_playlist_count_without_playlist_details(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get(
        "/api/v1/tracks",
        params={"spotify_playlist_id": "sp_pl_1", "page_size": 50},
    )
    assert res.status_code == 200
    item = res.json()["items"][0]
    assert item["playlist_count"] >= 1
    assert item["playlists"] == []


def test_count_query_uses_minimal_joins(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'joins.sqlite'}")
    reset_engine()
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
        repo = TracksRepository()
        filters = {"sort": "liked_added_at", "order": "desc"}
        count_sql = str(
            repo.build_count_query(session, filters=filters).compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        ids_sql = str(
            repo.build_ids_query(session, filters=filters).compile(
                compile_kwargs={"literal_binds": True}
            )
        )
    assert "ORDER BY" not in count_sql.upper()
    assert "DISTINCT" not in count_sql.upper()
    assert "ORDER BY" in ids_sql.upper()


def test_search_sql_query_count_bounded(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'sqlcount.sqlite'}")
    reset_engine()
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)

    query_count = 0

    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        stats = _sql_stats.get()
        if stats is not None:
            query_count += 1

    service = TrackSearchService()
    with track_search_perf_context():
        service.search(TrackSearchFilters(page=1, page_size=50))

    assert query_count <= 8


def test_large_library_page_latency(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'large.sqlite'}")
    reset_engine()
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_large_library(session, track_count=5000)

    service = TrackSearchService()
    start = time.perf_counter()
    result = service.search(
        TrackSearchFilters(page=1, page_size=50, sort="liked_added_at", order="desc")
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    assert result.pagination.total == 5000
    assert len(result.items) == 50
    assert elapsed_ms < 3000.0


def test_large_library_page2_latency(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'large2.sqlite'}")
    reset_engine()
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_large_library(session, track_count=5000)

    service = TrackSearchService()
    start = time.perf_counter()
    result = service.search(
        TrackSearchFilters(page=2, page_size=50, sort="liked_added_at", order="desc")
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    assert len(result.items) == 50
    assert elapsed_ms < 3000.0


def test_playlist_count_aggregation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'plcount.sqlite'}")
    reset_engine()
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_large_library(session, track_count=20)
        repo = TracksRepository()
        counts = repo.fetch_playlist_counts_for_tracks(
            session, ["sp_track_000000", "sp_track_000010"]
        )
    assert counts.get("sp_track_000000", 0) == 1
    assert counts.get("sp_track_000010", 0) == 1
