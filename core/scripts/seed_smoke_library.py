#!/usr/bin/env python3
"""Minimal library seed for Docker smoke validation (not for production)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_library import LikedTrack, SpotifyTrack, Track


def main() -> None:
    init_db()
    now = datetime(2026, 1, 15, 12, 0, 0)
    engine = get_engine()
    with Session(engine) as session:
        existing = session.scalar(select(Track.id).limit(1))
        if existing is not None:
            count = session.scalar(select(Track.id))
            print(f"skip: library already has tracks (id>={existing})")
            return
        for i in range(1, 11):
            sp_id = f"sp_smoke_{i:03d}"
            t = Track(
                name=f"Smoke Track {i}",
                normalized_title=f"smoke track {i}",
                duration_ms=180000,
                raw_json="{}",
                created_at=now,
                updated_at=now,
            )
            session.add(t)
            session.flush()
            session.add(
                SpotifyTrack(
                    spotify_track_id=sp_id,
                    track_id=t.id,
                    spotify_uri=f"spotify:track:smoke{i:03d}",
                    market_status="available",
                    raw_json="{}",
                    last_seen_at=now,
                )
            )
            session.add(
                LikedTrack(
                    spotify_track_id=sp_id,
                    added_at=now,
                    is_current=True,
                    raw_json="{}",
                )
            )
        session.commit()
        print("seeded 10 tracks for smoke validation")


if __name__ == "__main__":
    main()
