#!/usr/bin/env python3
"""Backfill albums.cover_* from albums.raw_json (Spotify album.images).

Requires the core virtualenv (SQLAlchemy, Alembic). Do not run with system Python.

  cd core && uv run python scripts/backfill_album_covers.py --dry-run

From repo root:

  uv run --project core python core/scripts/backfill_album_covers.py --dry-run

Against the Docker SQLite volume (after `docker compose up`):

  docker compose exec core-api uv run python scripts/backfill_album_covers.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1]
_REPO_ROOT = _CORE.parent
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))


def _usage_hint() -> str:
    args_tail = " ".join(sys.argv[1:])
    dry = f" {args_tail}".rstrip()
    return (
        "This script must run inside the core uv environment (SQLAlchemy is not on system Python).\n"
        "From repo root:\n"
        f"  uv run --project core python core/scripts/backfill_album_covers.py{dry}\n"
        "From core/:\n"
        f"  cd core && uv run python scripts/backfill_album_covers.py{dry}\n"
        "Inside Docker (DB on spotify_curator_data volume):\n"
        f"  docker compose exec core-api uv run python scripts/backfill_album_covers.py{dry}"
    )


try:
    from sqlalchemy import inspect, select
    from sqlalchemy.orm import Session
except ImportError:
    print(_usage_hint(), file=sys.stderr)
    raise SystemExit(1) from None

from app.database.engine import get_engine, reset_engine
from app.database.models_library import Album
from app.library.album_cover import apply_cover_to_album, extract_cover_from_images


def _resolve_database_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url
    env = os.getenv("DATABASE_URL")
    if env:
        return env
    candidates = [
        _REPO_ROOT / "data" / "spotify_curator.sqlite",
        Path("/app/data/spotify_curator.sqlite"),
    ]
    for path in candidates:
        if path.is_file():
            return f"sqlite:///{path.as_posix()}"
    return "sqlite:////app/data/spotify_curator.sqlite"


def _ensure_cover_columns() -> None:
    engine = get_engine()
    insp = inspect(engine)
    if not insp.has_table("albums"):
        raise SystemExit("Table albums not found. Check DATABASE_URL and run migrations first.")
    names = {col["name"] for col in insp.get_columns("albums")}
    if "cover_image_url" in names:
        return
    from app.database.migrate import run_migrations

    print("Missing albums.cover_* columns — running Alembic migrations to head...")
    run_migrations()
    reset_engine()
    insp = inspect(get_engine())
    names = {col["name"] for col in insp.get_columns("albums")}
    if "cover_image_url" not in names:
        raise SystemExit(
            "Migration 0004_album_covers did not apply. "
            "Start the core once (`docker compose up -d`) or run: "
            "cd core && uv run alembic upgrade head"
        )


def run(*, dry_run: bool = False) -> dict[str, int]:
    engine = get_engine()
    updated = 0
    skipped = 0
    errors = 0
    rows: list[Album] = []
    with Session(engine) as session:
        rows = list(session.execute(select(Album)).scalars().all())
        for album in rows:
            if not album.raw_json or album.raw_json == "{}":
                skipped += 1
                continue
            try:
                data = json.loads(album.raw_json)
            except json.JSONDecodeError:
                errors += 1
                continue
            cover = extract_cover_from_images(data.get("images"))
            if not cover.url:
                skipped += 1
                continue
            if (
                album.cover_image_url == cover.url
                and album.cover_image_width == cover.width
                and album.cover_image_height == cover.height
            ):
                skipped += 1
                continue
            if not dry_run:
                apply_cover_to_album(album, cover)
            updated += 1
        if not dry_run:
            session.commit()
    return {"updated": updated, "skipped": skipped, "errors": errors, "total": len(rows)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill album cover URLs from raw_json",
        epilog="Use: uv run --project core python core/scripts/backfill_album_covers.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLite URL (default: DATABASE_URL, else ./data/spotify_curator.sqlite if present)",
    )
    args = parser.parse_args()
    db_url = _resolve_database_url(args.database_url)
    os.environ["DATABASE_URL"] = db_url
    reset_engine()
    _ensure_cover_columns()
    print(f"database={db_url}")
    stats = run(dry_run=args.dry_run)
    mode = "dry-run" if args.dry_run else "applied"
    print(f"[{mode}] updated={stats['updated']} skipped={stats['skipped']} errors={stats['errors']} total={stats['total']}")


if __name__ == "__main__":
    main()
