from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_library import LikedTrack, SpotifyTrack
from app.database.models_snapshots import (
    LikedTrackSnapshot,
    PlaylistSnapshot,
    PlaylistTrackSnapshot,
    Snapshot,
)

STATUS_REMOVED_FROM_LIKED = "removed_from_liked"
STATUS_MISSING_FROM_CURRENT_IMPORT = "missing_from_current_import"
STATUS_UNAVAILABLE_ON_SPOTIFY = "unavailable_on_spotify"
STATUS_NULL_PLAYLIST_TRACK = "null_playlist_track"
STATUS_POSSIBLY_RELINKED = "possibly_relinked"


@dataclass(frozen=True)
class TrackStatusEntry:
    status: str
    spotify_track_id: str | None
    spotify_playlist_id: str | None
    position: int | None
    context: dict


def _liked_set(session: Session, snapshot_id: str) -> set[str]:
    rows = session.execute(
        select(LikedTrackSnapshot.spotify_track_id).where(
            LikedTrackSnapshot.snapshot_id == snapshot_id
        )
    ).scalars().all()
    return set(rows)


def _playlist_set(session: Session, snapshot_id: str) -> set[str]:
    rows = session.execute(
        select(PlaylistSnapshot.spotify_playlist_id).where(
            PlaylistSnapshot.snapshot_id == snapshot_id
        )
    ).scalars().all()
    return set(rows)


def _playlist_items(
    session: Session, snapshot_id: str, playlist_id: str
) -> dict[int, str | None]:
    rows = session.execute(
        select(PlaylistTrackSnapshot.position, PlaylistTrackSnapshot.spotify_track_id).where(
            PlaylistTrackSnapshot.snapshot_id == snapshot_id,
            PlaylistTrackSnapshot.spotify_playlist_id == playlist_id,
        )
    ).all()
    return {pos: tid for pos, tid in rows}


def _track_row(session: Session, spotify_track_id: str | None) -> SpotifyTrack | None:
    if not spotify_track_id:
        return None
    return session.get(SpotifyTrack, spotify_track_id)


def _classify_track(
    session: Session,
    *,
    spotify_track_id: str | None,
    in_from_liked: bool,
    in_to_liked: bool,
    in_current_liked: bool,
    playlist_id: str | None = None,
    position: int | None = None,
) -> list[TrackStatusEntry]:
    statuses: list[TrackStatusEntry] = []
    ctx: dict = {"spotify_track_id": spotify_track_id}

    if spotify_track_id is None:
        if playlist_id is not None:
            statuses.append(
                TrackStatusEntry(
                    status=STATUS_NULL_PLAYLIST_TRACK,
                    spotify_track_id=None,
                    spotify_playlist_id=playlist_id,
                    position=position,
                    context=ctx,
                )
            )
        return statuses

    if in_from_liked and not in_to_liked:
        statuses.append(
            TrackStatusEntry(
                status=STATUS_REMOVED_FROM_LIKED,
                spotify_track_id=spotify_track_id,
                spotify_playlist_id=playlist_id,
                position=position,
                context=ctx,
            )
        )

    if in_to_liked and not in_current_liked:
        statuses.append(
            TrackStatusEntry(
                status=STATUS_MISSING_FROM_CURRENT_IMPORT,
                spotify_track_id=spotify_track_id,
                spotify_playlist_id=playlist_id,
                position=position,
                context=ctx,
            )
        )

    row = _track_row(session, spotify_track_id)
    if row is not None:
        if row.is_playable is False:
            statuses.append(
                TrackStatusEntry(
                    status=STATUS_UNAVAILABLE_ON_SPOTIFY,
                    spotify_track_id=spotify_track_id,
                    spotify_playlist_id=playlist_id,
                    position=position,
                    context=ctx,
                )
            )
        if row.linked_from_spotify_track_id:
            statuses.append(
                TrackStatusEntry(
                    status=STATUS_POSSIBLY_RELINKED,
                    spotify_track_id=spotify_track_id,
                    spotify_playlist_id=playlist_id,
                    position=position,
                    context={
                        **ctx,
                        "linked_from_spotify_track_id": row.linked_from_spotify_track_id,
                    },
                )
            )

    return statuses


def diff_snapshots(from_snapshot_id: str, to_snapshot_id: str) -> dict:
    engine = get_engine()
    with Session(engine) as session:
        from_snap = session.get(Snapshot, from_snapshot_id)
        to_snap = session.get(Snapshot, to_snapshot_id)
        if from_snap is None or to_snap is None:
            raise ValueError("Snapshot not found.")

        from_liked = _liked_set(session, from_snapshot_id)
        to_liked = _liked_set(session, to_snapshot_id)
        current_liked = set(session.execute(select(LikedTrack.spotify_track_id)).scalars().all())

        liked_added = sorted(to_liked - from_liked)
        liked_removed = sorted(from_liked - to_liked)

        from_playlists = _playlist_set(session, from_snapshot_id)
        to_playlists = _playlist_set(session, to_snapshot_id)
        playlists_added = sorted(to_playlists - from_playlists)
        playlists_removed = sorted(from_playlists - to_playlists)

        playlists_changed: list[dict] = []
        for pid in sorted(from_playlists & to_playlists):
            from_items = _playlist_items(session, from_snapshot_id, pid)
            to_items = _playlist_items(session, to_snapshot_id, pid)
            if from_items != to_items:
                playlists_changed.append(
                    {
                        "spotify_playlist_id": pid,
                        "from_item_count": len(from_items),
                        "to_item_count": len(to_items),
                    }
                )

        track_statuses: list[dict] = []
        seen: set[tuple[str | None, str | None, int | None]] = set()

        for tid in liked_removed:
            for entry in _classify_track(
                session,
                spotify_track_id=tid,
                in_from_liked=True,
                in_to_liked=False,
                in_current_liked=tid in current_liked,
            ):
                key = (entry.spotify_track_id, entry.spotify_playlist_id, entry.position)
                if key not in seen:
                    seen.add(key)
                    track_statuses.append(
                        {
                            "status": entry.status,
                            "spotify_track_id": entry.spotify_track_id,
                            "spotify_playlist_id": entry.spotify_playlist_id,
                            "position": entry.position,
                            "context": entry.context,
                        }
                    )

        for tid in to_liked - from_liked:
            for entry in _classify_track(
                session,
                spotify_track_id=tid,
                in_from_liked=False,
                in_to_liked=True,
                in_current_liked=tid in current_liked,
            ):
                key = (entry.spotify_track_id, entry.spotify_playlist_id, entry.position)
                if key not in seen:
                    seen.add(key)
                    track_statuses.append(
                        {
                            "status": entry.status,
                            "spotify_track_id": entry.spotify_track_id,
                            "spotify_playlist_id": entry.spotify_playlist_id,
                            "position": entry.position,
                            "context": entry.context,
                        }
                    )

        for pid in sorted(to_playlists):
            to_items = _playlist_items(session, to_snapshot_id, pid)
            from_items = (
                _playlist_items(session, from_snapshot_id, pid) if pid in from_playlists else {}
            )
            for pos, tid in to_items.items():
                if tid is None or from_items.get(pos) != tid:
                    for entry in _classify_track(
                        session,
                        spotify_track_id=tid,
                        in_from_liked=tid in from_liked if tid else False,
                        in_to_liked=tid in to_liked if tid else False,
                        in_current_liked=tid in current_liked if tid else False,
                        playlist_id=pid,
                        position=pos,
                    ):
                        key = (entry.spotify_track_id, entry.spotify_playlist_id, entry.position)
                        if key not in seen:
                            seen.add(key)
                            track_statuses.append(
                                {
                                    "status": entry.status,
                                    "spotify_track_id": entry.spotify_track_id,
                                    "spotify_playlist_id": entry.spotify_playlist_id,
                                    "position": entry.position,
                                    "context": entry.context,
                                }
                            )

        summary = {
            "liked": {
                "added_count": len(liked_added),
                "removed_count": len(liked_removed),
            },
            "playlists": {
                "added_count": len(playlists_added),
                "removed_count": len(playlists_removed),
                "changed_count": len(playlists_changed),
            },
            "track_status_counts": {},
        }
        for item in track_statuses:
            st = item["status"]
            summary["track_status_counts"][st] = summary["track_status_counts"].get(st, 0) + 1

        return {
            "from_snapshot_id": from_snapshot_id,
            "to_snapshot_id": to_snapshot_id,
            "liked": {
                "added": liked_added,
                "removed": liked_removed,
            },
            "playlists": {
                "added": playlists_added,
                "removed": playlists_removed,
                "changed": playlists_changed,
            },
            "tracks": {"statuses": track_statuses},
            "summary": summary,
        }
