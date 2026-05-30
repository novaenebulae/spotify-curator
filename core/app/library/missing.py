from __future__ import annotations

import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_library import Album, Artist, SpotifyTrack, Track, TrackArtist
from app.database.models_snapshots import Snapshot
from app.library.diff import (
    STATUS_MISSING_FROM_CURRENT_IMPORT,
    STATUS_NULL_PLAYLIST_TRACK,
    STATUS_POSSIBLY_RELINKED,
    STATUS_REMOVED_FROM_LIKED,
    STATUS_UNAVAILABLE_ON_SPOTIFY,
    diff_snapshots,
)
from app.library.snapshots import SnapshotService
from app.observability.errors import ApiError

ALL_STATUSES = frozenset(
    {
        STATUS_REMOVED_FROM_LIKED,
        STATUS_MISSING_FROM_CURRENT_IMPORT,
        STATUS_UNAVAILABLE_ON_SPOTIFY,
        STATUS_NULL_PLAYLIST_TRACK,
        STATUS_POSSIBLY_RELINKED,
    }
)


class MissingTracksService:
    def __init__(self) -> None:
        self._snapshots = SnapshotService()

    def list_missing(
        self,
        *,
        snapshot_id: str | None = None,
        from_snapshot_id: str | None = None,
        to_snapshot_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        if status and status not in ALL_STATUSES:
            raise ApiError(
                code="VALIDATION_ERROR",
                message=f"Invalid status: {status}",
                status_code=400,
            )

        from_id, to_id = self._resolve_snapshot_pair(
            snapshot_id=snapshot_id,
            from_snapshot_id=from_snapshot_id,
            to_snapshot_id=to_snapshot_id,
        )
        diff = diff_snapshots(from_id, to_id)
        statuses = diff["tracks"]["statuses"]
        if status:
            statuses = [s for s in statuses if s.get("status") == status]

        summary = {
            STATUS_REMOVED_FROM_LIKED: 0,
            STATUS_MISSING_FROM_CURRENT_IMPORT: 0,
            STATUS_UNAVAILABLE_ON_SPOTIFY: 0,
            STATUS_NULL_PLAYLIST_TRACK: 0,
            STATUS_POSSIBLY_RELINKED: 0,
        }
        for item in diff["tracks"]["statuses"]:
            st = item.get("status")
            if st in summary:
                summary[st] += 1

        engine = get_engine()
        with Session(engine) as session:
            to_snap = session.get(Snapshot, to_id)
            detected_at = to_snap.created_at.isoformat() if to_snap and to_snap.created_at else None

            items: list[dict[str, Any]] = []
            for entry in statuses:
                sp_id = entry.get("spotify_track_id")
                track_meta = self._track_meta(session, sp_id) if sp_id else None
                items.append(
                    {
                        "track_id": track_meta["track_id"] if track_meta else None,
                        "spotify_track_id": sp_id,
                        "title": track_meta["title"] if track_meta else None,
                        "artist_names": track_meta["artist_names"] if track_meta else [],
                        "album_name": track_meta["album_name"] if track_meta else None,
                        "cover_image_url": track_meta.get("cover_image_url")
                        if track_meta
                        else None,
                        "cover_image_width": track_meta.get("cover_image_width")
                        if track_meta
                        else None,
                        "cover_image_height": track_meta.get("cover_image_height")
                        if track_meta
                        else None,
                        "status": entry.get("status"),
                        "source_snapshot_id": from_id,
                        "target_snapshot_id": to_id,
                        "detected_at": detected_at,
                        "context": entry.get("context") or {},
                    }
                )

        page = max(1, page)
        page_size = min(200, max(1, page_size))
        total = len(items)
        offset = (page - 1) * page_size
        page_items = items[offset : offset + page_size]
        total_pages = math.ceil(total / page_size) if total else 0

        return {
            "items": page_items,
            "summary": summary,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        }

    def _resolve_snapshot_pair(
        self,
        *,
        snapshot_id: str | None,
        from_snapshot_id: str | None,
        to_snapshot_id: str | None,
    ) -> tuple[str, str]:
        if from_snapshot_id and to_snapshot_id:
            return from_snapshot_id, to_snapshot_id

        snapshots = self._snapshots.list_snapshots()
        if not snapshots:
            raise ApiError(
                code="VALIDATION_ERROR",
                message="No snapshots available.",
                status_code=400,
            )

        if snapshot_id:
            ids = [s["id"] for s in snapshots]
            if snapshot_id not in ids:
                raise ApiError(code="NOT_FOUND", message="Snapshot not found.", status_code=404)
            idx = ids.index(snapshot_id)
            if idx + 1 >= len(snapshots):
                raise ApiError(
                    code="VALIDATION_ERROR",
                    message="No previous snapshot to compare.",
                    status_code=400,
                )
            return snapshots[idx + 1]["id"], snapshot_id

        if len(snapshots) < 2:
            raise ApiError(
                code="VALIDATION_ERROR",
                message="At least two snapshots are required.",
                status_code=400,
            )
        return snapshots[1]["id"], snapshots[0]["id"]

    def _track_meta(self, session: Session, spotify_track_id: str) -> dict[str, Any] | None:
        stmt = (
            select(
                Track.id,
                Track.name,
                Album.name,
                Album.cover_image_url,
                Album.cover_image_width,
                Album.cover_image_height,
            )
            .join(SpotifyTrack, SpotifyTrack.track_id == Track.id)
            .outerjoin(Album, Album.id == SpotifyTrack.album_id)
            .where(SpotifyTrack.spotify_track_id == spotify_track_id)
        )
        row = session.execute(stmt).one_or_none()
        if row is None:
            return None
        track_id, title, album_name, cover_url, cw, ch = row
        artist_stmt = (
            select(Artist.name)
            .join(TrackArtist, TrackArtist.artist_id == Artist.id)
            .where(TrackArtist.track_id == track_id)
            .order_by(TrackArtist.position)
        )
        artist_names = list(session.execute(artist_stmt).scalars().all())
        return {
            "track_id": track_id,
            "title": title,
            "artist_names": artist_names,
            "album_name": album_name,
            "cover_image_url": cover_url,
            "cover_image_width": cw,
            "cover_image_height": ch,
        }
