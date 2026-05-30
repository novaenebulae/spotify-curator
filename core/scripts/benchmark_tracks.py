#!/usr/bin/env python3
"""Benchmark GET /api/v1/tracks scenarios (local DB or HTTP)."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

# Allow running from repo root: uv run python core/scripts/benchmark_tracks.py
_CORE = Path(__file__).resolve().parents[1]
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

SCENARIOS: list[tuple[str, dict[str, str | int]]] = [
    ("page1_default", {"page": 1, "page_size": 50, "sort": "liked_added_at", "order": "desc"}),
    ("page2_default", {"page": 2, "page_size": 50, "sort": "liked_added_at", "order": "desc"}),
    ("search_q", {"page": 1, "page_size": 50, "q": "a"}),
    ("sort_liked_desc", {"page": 1, "page_size": 50, "sort": "liked_added_at", "order": "desc"}),
]


def _run_direct(params: dict[str, str | int], runs: int) -> list[float]:
    os.environ["TRACKS_PERF_LOG"] = "1"
    from sqlalchemy.orm import Session

    from app.database.engine import get_engine, reset_engine
    from app.database.init_db import init_db
    from app.library.schemas import TrackSearchFilters
    from app.library.search import TrackSearchService
    from app.observability.sql_perf import get_track_search_perf, track_search_perf_context

    reset_engine()
    init_db()
    service = TrackSearchService()
    allowed = set(TrackSearchFilters.model_fields)
    timings: list[float] = []
    for _ in range(runs):
        filters = TrackSearchFilters(
            **{k: v for k, v in params.items() if k in allowed},
        )
        start = time.perf_counter()
        with track_search_perf_context():
            service.search(filters)
        timings.append((time.perf_counter() - start) * 1000.0)
    return timings


def _explain_plans(params: dict[str, str | int]) -> None:
    from sqlalchemy.orm import Session

    from app.database.engine import get_engine, reset_engine
    from app.database.init_db import init_db
    from app.database.repositories.tracks import TracksRepository
    from app.library.schemas import TrackSearchFilters

    reset_engine()
    init_db()
    repo = TracksRepository()
    f = TrackSearchFilters(**params)
    filter_dict = f.model_dump(exclude_none=True)
    filter_dict["sort"] = f.sort
    filter_dict["order"] = f.order
    engine = get_engine()
    with Session(engine) as session:
        count_q = repo.build_count_query(session, filters=filter_dict)
        ids_q = repo.build_ids_query(session, filters=filter_dict)
        for label, stmt in [("COUNT", count_q), ("IDS", ids_q)]:
            sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
            print(f"\n--- EXPLAIN {label} ---")
            print(sql[:500] + ("..." if len(sql) > 500 else ""))
            rows = session.connection().exec_driver_sql(f"EXPLAIN QUERY PLAN {sql}").fetchall()
            for row in rows:
                print(" ", row)


def _run_http(base_url: str, params: dict[str, str | int], runs: int) -> list[float]:
    import urllib.parse
    import urllib.request

    qs = urllib.parse.urlencode({k: str(v) for k, v in params.items()})
    url = f"{base_url.rstrip('/')}/api/v1/tracks?{qs}"
    timings: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
            _ = len(body)
        timings.append((time.perf_counter() - start) * 1000.0)
    return timings


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark GET /tracks")
    parser.add_argument("--database-url", default=None, help="SQLite URL for direct mode")
    parser.add_argument("--base-url", default=None, help="HTTP base e.g. http://127.0.0.1:8765")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--q", default=None, help="Override search term for search_q scenario")
    parser.add_argument("--playlist-id", type=int, default=None)
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    scenarios = list(SCENARIOS)
    if args.q:
        scenarios = [
            (n, {**p, "q": args.q} if n == "search_q" else p) for n, p in scenarios
        ]
    if args.playlist_id is not None:
        scenarios.append(
            (
                "playlist_filter",
                {
                    "page": 1,
                    "page_size": 50,
                    "playlist_id": args.playlist_id,
                    "sort": "liked_added_at",
                    "order": "desc",
                },
            )
        )

    if args.explain:
        _explain_plans(dict(scenarios[0][1]))
        return

    results: dict[str, dict[str, float | int]] = {}
    for name, params in scenarios:
        if args.base_url:
            timings = _run_http(args.base_url, params, args.runs)
        else:
            timings = _run_direct(params, args.runs)
        med = statistics.median(timings)
        results[name] = {
            "median_ms": round(med, 2),
            "min_ms": round(min(timings), 2),
            "max_ms": round(max(timings), 2),
        }
        print(f"{name:20} median={med:.1f}ms  runs={timings}")

    if args.json:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
