from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_library import LikedTrack
from app.database.models_playlists import Playlist, PlaylistTrack
from app.database.models_snapshots import (
    LikedTrackSnapshot,
    PlaylistSnapshot,
    PlaylistTrackSnapshot,
    Snapshot,
)
from app.library.diff import diff_snapshots


class SnapshotService:
    def create_snapshot(self, snapshot_type: str) -> str:
        if snapshot_type not in ("full", "liked", "playlists"):
            raise ValueError("Invalid snapshot type.")

        snapshot_id = uuid.uuid4().hex
        now = datetime.now(tz=UTC).replace(tzinfo=None)

        engine = get_engine()
        with Session(engine) as session:
            snap = Snapshot(
                id=snapshot_id,
                snapshot_type=snapshot_type,
                status="completed",
                created_at=now,
                track_count=0,
                playlist_count=0,
                metadata_json=json.dumps({}),
            )
            session.add(snap)
            session.flush()

            if snapshot_type in ("full", "liked"):
                liked_rows = session.execute(select(LikedTrack)).scalars().all()
                for row in liked_rows:
                    session.add(
                        LikedTrackSnapshot(
                            snapshot_id=snapshot_id,
                            spotify_track_id=row.spotify_track_id,
                            added_at=row.added_at,
                        )
                    )
                snap.track_count = len(liked_rows)

            if snapshot_type in ("full", "playlists"):
                playlists = session.execute(select(Playlist)).scalars().all()
                snap.playlist_count = len(playlists)
                for pl in playlists:
                    items = session.execute(
                        select(PlaylistTrack).where(
                            PlaylistTrack.spotify_playlist_id == pl.spotify_playlist_id
                        )
                    ).scalars().all()
                    session.add(
                        PlaylistSnapshot(
                            snapshot_id=snapshot_id,
                            spotify_playlist_id=pl.spotify_playlist_id,
                            spotify_snapshot_id=pl.spotify_snapshot_id,
                            item_count=len(items),
                        )
                    )
                    for it in items:
                        session.add(
                            PlaylistTrackSnapshot(
                                snapshot_id=snapshot_id,
                                spotify_playlist_id=pl.spotify_playlist_id,
                                position=it.position,
                                spotify_track_id=it.spotify_track_id,
                                added_at=it.added_at,
                            )
                        )

            session.commit()

        return snapshot_id

    def list_snapshots(self) -> list[dict]:
        engine = get_engine()
        with Session(engine) as session:
            snaps = session.execute(
                select(Snapshot).order_by(Snapshot.created_at.desc())
            ).scalars().all()
            return [
                {
                    "id": s.id,
                    "type": s.snapshot_type,
                    "status": s.status,
                    "created_at": s.created_at.isoformat(),
                    "track_count": s.track_count,
                    "playlist_count": s.playlist_count,
                }
                for s in snaps
            ]

    def diff(self, from_snapshot_id: str, to_snapshot_id: str) -> dict:
        return diff_snapshots(from_snapshot_id, to_snapshot_id)

    def get_snapshot(self, snapshot_id: str) -> dict | None:
        engine = get_engine()
        with Session(engine) as session:
            s = session.get(Snapshot, snapshot_id)
            if s is None:
                return None
            return {
                "id": s.id,
                "type": s.snapshot_type,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "track_count": s.track_count,
                "playlist_count": s.playlist_count,
                "metadata": json.loads(s.metadata_json or "{}"),
            }

