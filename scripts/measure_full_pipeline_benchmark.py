#!/usr/bin/env python3
"""Full pipeline benchmark — all stages, host-side (no core-api container).

Reads SQLite directly so refresh/recompute OOM in core-api does not affect sampling.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

JOB_ID = "7d5cdb9ea98d4807bfa6068ce2408bd9"
DEFAULT_SQLITE = "/home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite"

STAGES = (
    "segment_download",
    "essentia_lowlevel",
    "essentia_tensorflow",
    "feature_aggregation",
    "audio_cleanup",
)

SHORT = {
    "segment_download": "dl",
    "essentia_lowlevel": "ll",
    "essentia_tensorflow": "tf",
    "feature_aggregation": "agg",
    "audio_cleanup": "cleanup",
}


def gpu_snapshot() -> str:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        if len(parts) >= 3:
            return f"VRAM {parts[0]}/{parts[1]} MiB, GPU {parts[2]}%"
    except Exception:
        pass
    return "GPU n/a"


def _bind_sql(sql: str, params: tuple[Any, ...]) -> tuple[str, dict[str, Any]]:
    if "?" not in sql:
        return sql, {}
    parts = sql.split("?")
    bound: dict[str, Any] = {}
    new_sql = parts[0]
    for i, part in enumerate(parts[1:], start=1):
        key = f"p{i}"
        bound[key] = params[i - 1]
        new_sql += f":{key}{part}"
    return new_sql, bound


class _SqliteReader:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        return self._conn.execute(sql, params)

    def close(self) -> None:
        self._conn.close()


class _SqlAlchemyReader:
    def __init__(self, database_url: str) -> None:
        from sqlalchemy import create_engine

        self._engine = create_engine(database_url, future=True)
        self._conn = self._engine.connect()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        from sqlalchemy import text

        bound_sql, bound = _bind_sql(sql, params)
        return self._conn.execute(text(bound_sql), bound)

    def close(self) -> None:
        self._conn.close()
        self._engine.dispose()


def connect_sqlite(sqlite_path: str) -> _SqliteReader:
    path = Path(sqlite_path)
    if not path.is_file():
        raise FileNotFoundError(f"SQLite not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return _SqliteReader(conn)


def connect_database_url(database_url: str) -> _SqlAlchemyReader:
    return _SqlAlchemyReader(database_url)


@contextmanager
def connect(
    *,
    sqlite_path: str | None = None,
    database_url: str | None = None,
) -> Iterator[Any]:
    if database_url:
        conn = connect_database_url(database_url)
    elif sqlite_path:
        conn = connect_sqlite(sqlite_path)
    else:
        raise ValueError("sqlite_path or database_url required")
    try:
        yield conn
    finally:
        conn.close()


def _row_val(row: Any, key: str) -> Any:
    if hasattr(row, "__getitem__") and not isinstance(row, dict):
        try:
            return row[key]
        except Exception:
            return getattr(row, key)
    return row[key]


def stage_success(conn: Any, job_id: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for stage in STAGES:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM job_items "
            "WHERE job_id=? AND stage_name=? AND status='success'",
            (job_id, stage),
        ).fetchone()
        out[stage] = int(_row_val(row, "n"))
    return out


def stage_status_breakdown(
    conn: Any, job_id: str, stage: str
) -> dict[str, int]:
    rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM job_items "
        "WHERE job_id=? AND stage_name=? GROUP BY status ORDER BY status",
        (job_id, stage),
    ).fetchall()
    return {str(_row_val(r, "status")): int(_row_val(r, "n")) for r in rows}


def tf_ready_pending(conn: Any, job_id: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM job_items tf
        JOIN job_items ll ON ll.job_id=tf.job_id AND ll.track_id=tf.track_id
          AND ll.stage_name='essentia_lowlevel' AND ll.status='success'
        WHERE tf.job_id=? AND tf.stage_name='essentia_tensorflow'
          AND tf.status='pending'
        """,
        (job_id,),
    ).fetchone()
    return int(_row_val(row, "n"))


def agg_ready_pending(conn: Any, job_id: str) -> int:
    """Tracks with TF done but aggregation not yet success."""
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM job_items agg
        JOIN job_items tf ON tf.job_id=agg.job_id AND tf.track_id=agg.track_id
          AND tf.stage_name='essentia_tensorflow' AND tf.status='success'
        WHERE agg.job_id=? AND agg.stage_name='feature_aggregation'
          AND agg.status IN ('pending', 'running')
        """,
        (job_id,),
    ).fetchone()
    return int(_row_val(row, "n"))


def cleanup_ready_pending(conn: Any, job_id: str) -> int:
    """Tracks with aggregation done but cleanup not yet success."""
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM job_items cl
        JOIN job_items agg ON agg.job_id=cl.job_id AND agg.track_id=cl.track_id
          AND agg.stage_name='feature_aggregation' AND agg.status='success'
        WHERE cl.job_id=? AND cl.stage_name='audio_cleanup'
          AND cl.status IN ('pending', 'running')
        """,
        (job_id,),
    ).fetchone()
    return int(_row_val(row, "n"))


def snapshot(conn: Any, job_id: str) -> dict[str, int | str]:
    c = stage_success(conn, job_id)
    c["tf_ready"] = tf_ready_pending(conn, job_id)
    c["agg_ready"] = agg_ready_pending(conn, job_id)
    c["cleanup_ready"] = cleanup_ready_pending(conn, job_id)
    return c


def print_breakdown(conn: Any, job_id: str, title: str) -> None:
    print(f"\n--- {title} ---")
    for stage in ("feature_aggregation", "audio_cleanup"):
        bd = stage_status_breakdown(conn, job_id, stage)
        parts = " ".join(f"{k}={v}" for k, v in sorted(bd.items()))
        print(f"  {SHORT[stage]:>7}: {parts}")


def format_line(elapsed: float, c: dict[str, int | str]) -> str:
    return (
        f"t={elapsed:5.0f}s  "
        f"dl={c['segment_download']:4d}  ll={c['essentia_lowlevel']:4d}  "
        f"tf={c['essentia_tensorflow']:4d}  agg={c['feature_aggregation']:4d}  "
        f"cleanup={c['audio_cleanup']:4d}  "
        f"tf_q={c['tf_ready']:3d} agg_q={c['agg_ready']:3d} cl_q={c['cleanup_ready']:3d}  "
        f"{gpu_snapshot()}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Full pipeline stage benchmark (SQLite or Postgres)")
    parser.add_argument("--job-id", default=JOB_ID)
    parser.add_argument("--sqlite-path", default=os.environ.get("SQLITE_PATH", DEFAULT_SQLITE))
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="postgresql+psycopg://... (overrides --sqlite-path)",
    )
    parser.add_argument("--duration-sec", type=int, default=300)
    parser.add_argument("--interval-sec", type=int, default=30)
    parser.add_argument("--label", default="full-pipeline")
    args = parser.parse_args()

    db_label = args.database_url or args.sqlite_path
    with connect(
        sqlite_path=None if args.database_url else args.sqlite_path,
        database_url=args.database_url or None,
    ) as conn:
        job = conn.execute(
            "SELECT id, status, job_type FROM jobs WHERE id=?", (args.job_id,)
        ).fetchone()
        if job is None:
            print(f"Job not found: {args.job_id}", file=sys.stderr)
            return 1

        samples: list[tuple[float, dict[str, int | str]]] = []
        t0 = time.monotonic()
        print(f"=== {args.label} ===")
        print(f"job={args.job_id} status={_row_val(job, 'status')} type={_row_val(job, 'job_type')}")
        print(f"database={db_label}")
        print(f"duration={args.duration_sec}s interval={args.interval_sec}s")
        print(f"start_utc={datetime.now(timezone.utc).isoformat()}")
        print_breakdown(conn, args.job_id, "status at start (agg/cleanup)")

        while True:
            elapsed = time.monotonic() - t0
            if elapsed > args.duration_sec:
                break
            c = snapshot(conn, args.job_id)
            samples.append((elapsed, c))
            print(format_line(elapsed, c))
            if elapsed + args.interval_sec > args.duration_sec:
                break
            time.sleep(args.interval_sec)

        if len(samples) < 2:
            print("Not enough samples", file=sys.stderr)
            return 1

        first_t, first_c = samples[0]
        last_t, last_c = samples[-1]
        dt_min = max((last_t - first_t) / 60.0, 1e-6)

        print(f"\n--- rates ({args.label}, window {last_t - first_t:.0f}s) ---")
        for stage in STAGES:
            delta = int(last_c[stage]) - int(first_c[stage])
            rate = delta / dt_min
            print(f"  {SHORT[stage]:>7}: +{delta:4d}  => {rate:5.1f}/min")

        print(
            f"\n--- backlogs at end ---\n"
            f"  tf_ready_pending={last_c['tf_ready']}  "
            f"agg_ready_pending={last_c['agg_ready']}  "
            f"cleanup_ready_pending={last_c['cleanup_ready']}"
        )
        print_breakdown(conn, args.job_id, "status at end (agg/cleanup)")
        print(f"end_utc={datetime.now(timezone.utc).isoformat()} {gpu_snapshot()}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
