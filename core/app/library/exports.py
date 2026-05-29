from __future__ import annotations

import csv
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_library import LikedTrack, SpotifyTrack, Track
from app.database.models_playlists import Playlist, PlaylistTrack
from app.database.models_snapshots import (
    LikedTrackSnapshot,
    PlaylistSnapshot,
    PlaylistTrackSnapshot,
)
from app.library.diff import diff_snapshots
from app.library.snapshots import SnapshotService
from app.settings.config import settings


def get_export_dir() -> Path:
    export_dir = os.getenv("EXPORT_DIR", settings.export_dir)
    path = Path(export_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _timestamp_slug() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: object) -> int:
    if isinstance(payload, list):
        row_count = len(payload)
    elif isinstance(payload, dict):
        row_count = len(payload)
    else:
        row_count = 1
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return row_count


def export_liked_tracks(*, fmt: str) -> dict:
    if fmt not in ("csv", "json"):
        raise ValueError("Invalid format. Use csv or json.")

    engine = get_engine()
    rows: list[dict] = []
    with Session(engine) as session:
        stmt = (
            select(
                LikedTrack.spotify_track_id,
                LikedTrack.added_at,
                Track.name,
                Track.duration_ms,
                Track.explicit,
                Track.popularity,
                SpotifyTrack.spotify_uri,
                SpotifyTrack.is_playable,
            )
            .join(SpotifyTrack, LikedTrack.spotify_track_id == SpotifyTrack.spotify_track_id)
            .join(Track, SpotifyTrack.track_id == Track.id)
            .order_by(LikedTrack.added_at.desc().nullslast())
        )
        for row in session.execute(stmt).all():
            rows.append(
                {
                    "spotify_track_id": row.spotify_track_id,
                    "added_at": row.added_at.isoformat() if row.added_at else "",
                    "name": row.name,
                    "duration_ms": row.duration_ms,
                    "explicit": row.explicit,
                    "popularity": row.popularity,
                    "spotify_uri": row.spotify_uri,
                    "is_playable": row.is_playable,
                }
            )

    export_dir = get_export_dir()
    filename = f"liked_tracks_{_timestamp_slug()}.{fmt}"
    path = export_dir / filename

    if fmt == "json":
        row_count = _write_json(path, rows)
    else:
        fieldnames = list(rows[0].keys()) if rows else [
            "spotify_track_id",
            "added_at",
            "name",
            "duration_ms",
            "explicit",
            "popularity",
            "spotify_uri",
            "is_playable",
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        row_count = len(rows)

    return {"path": str(path), "filename": filename, "row_count": row_count}


def export_playlists(*, fmt: str) -> dict:
    if fmt not in ("csv", "json"):
        raise ValueError("Invalid format. Use csv or json.")

    engine = get_engine()
    flat_rows: list[dict] = []
    nested: list[dict] = []

    with Session(engine) as session:
        playlists = session.execute(select(Playlist).order_by(Playlist.name)).scalars().all()
        for pl in playlists:
            items = session.execute(
                select(PlaylistTrack)
                .where(PlaylistTrack.spotify_playlist_id == pl.spotify_playlist_id)
                .order_by(PlaylistTrack.position)
            ).scalars().all()
            item_payloads = []
            for it in items:
                track_name = ""
                if it.spotify_track_id:
                    sp = session.get(SpotifyTrack, it.spotify_track_id)
                    if sp:
                        tr = session.get(Track, sp.track_id)
                        if tr:
                            track_name = tr.name
                item_payload = {
                    "position": it.position,
                    "spotify_track_id": it.spotify_track_id,
                    "track_name": track_name,
                    "added_at": it.added_at.isoformat() if it.added_at else "",
                    "added_by_spotify_user_id": it.added_by_spotify_user_id,
                }
                item_payloads.append(item_payload)
                flat_rows.append(
                    {
                        "spotify_playlist_id": pl.spotify_playlist_id,
                        "playlist_name": pl.name,
                        "playlist_uri": pl.spotify_uri,
                        "owner_spotify_user_id": pl.owner_spotify_user_id,
                        **item_payload,
                    }
                )
            nested.append(
                {
                    "spotify_playlist_id": pl.spotify_playlist_id,
                    "name": pl.name,
                    "spotify_uri": pl.spotify_uri,
                    "owner_spotify_user_id": pl.owner_spotify_user_id,
                    "is_public": pl.is_public,
                    "collaborative": pl.collaborative,
                    "item_count": len(item_payloads),
                    "items": item_payloads,
                }
            )

    export_dir = get_export_dir()
    filename = f"playlists_{_timestamp_slug()}.{fmt}"
    path = export_dir / filename

    if fmt == "json":
        row_count = _write_json(path, nested)
    else:
        fieldnames = list(flat_rows[0].keys()) if flat_rows else [
            "spotify_playlist_id",
            "playlist_name",
            "playlist_uri",
            "owner_spotify_user_id",
            "position",
            "spotify_track_id",
            "track_name",
            "added_at",
            "added_by_spotify_user_id",
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flat_rows)
        row_count = len(flat_rows)

    return {"path": str(path), "filename": filename, "row_count": row_count}


def export_snapshot(*, snapshot_id: str, fmt: str = "json") -> dict:
    if fmt != "json":
        raise ValueError("Snapshot export supports json only.")

    svc = SnapshotService()
    meta = svc.get_snapshot(snapshot_id)
    if meta is None:
        raise ValueError("Snapshot not found.")

    engine = get_engine()
    with Session(engine) as session:
        liked = session.execute(
            select(LikedTrackSnapshot).where(LikedTrackSnapshot.snapshot_id == snapshot_id)
        ).scalars().all()
        playlists = session.execute(
            select(PlaylistSnapshot).where(PlaylistSnapshot.snapshot_id == snapshot_id)
        ).scalars().all()
        playlist_tracks = session.execute(
            select(PlaylistTrackSnapshot).where(PlaylistTrackSnapshot.snapshot_id == snapshot_id)
        ).scalars().all()

    payload = {
        "snapshot": meta,
        "liked_tracks": [
            {
                "spotify_track_id": r.spotify_track_id,
                "added_at": r.added_at.isoformat() if r.added_at else None,
            }
            for r in liked
        ],
        "playlists": [
            {
                "spotify_playlist_id": r.spotify_playlist_id,
                "spotify_snapshot_id": r.spotify_snapshot_id,
                "item_count": r.item_count,
            }
            for r in playlists
        ],
        "playlist_tracks": [
            {
                "spotify_playlist_id": r.spotify_playlist_id,
                "position": r.position,
                "spotify_track_id": r.spotify_track_id,
                "added_at": r.added_at.isoformat() if r.added_at else None,
            }
            for r in playlist_tracks
        ],
    }

    export_dir = get_export_dir()
    filename = f"snapshot_{snapshot_id[:12]}_{_timestamp_slug()}.json"
    path = export_dir / filename
    row_count = _write_json(path, payload)
    return {"path": str(path), "filename": filename, "row_count": row_count}


def export_diff(*, from_snapshot_id: str, to_snapshot_id: str, fmt: str = "json") -> dict:
    if fmt != "json":
        raise ValueError("Diff export supports json only.")

    payload = diff_snapshots(from_snapshot_id, to_snapshot_id)
    export_dir = get_export_dir()
    filename = f"diff_{from_snapshot_id[:8]}_{to_snapshot_id[:8]}_{_timestamp_slug()}.json"
    path = export_dir / filename
    row_count = _write_json(path, payload)
    return {"path": str(path), "filename": filename, "row_count": row_count}
