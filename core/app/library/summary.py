from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_library import Album, Track
from app.database.models_playlists import Playlist
from app.library.snapshots import SnapshotService
from app.spotify.token_store import SpotifyTokenStore


class LibrarySummaryService:
    def __init__(self) -> None:
        self._snapshots = SnapshotService()

    def get_summary(self) -> dict[str, Any]:
        engine = get_engine()
        with Session(engine) as session:
            tracks_total = session.execute(select(func.count(Track.id))).scalar_one()
            playlists_total = session.execute(select(func.count(Playlist.id))).scalar_one()
            albums_total = session.execute(select(func.count(Album.id))).scalar_one()

        snapshots = self._snapshots.list_snapshots()
        latest = None
        if snapshots:
            s0 = snapshots[0]
            latest = {"id": s0["id"], "created_at": s0.get("created_at")}

        spotify_connected = SpotifyTokenStore().load() is not None

        return {
            "tracks_total": tracks_total,
            "playlists_total": playlists_total,
            "albums_total": albums_total,
            "latest_snapshot": latest,
            "spotify_connected": spotify_connected,
        }
