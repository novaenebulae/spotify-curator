from __future__ import annotations

from sqlalchemy import text

from app.database.engine import get_engine
from app.database.models import Base
from app.database.models_jobs import Job  # noqa: F401
from app.database.models_library import (  # noqa: F401
    Album,
    Artist,
    ExternalId,
    LikedTrack,
    SpotifyAlbum,
    SpotifyArtist,
    SpotifyTrack,
    Track,
    TrackArtist,
)
from app.database.models_playlists import Playlist, PlaylistTrack  # noqa: F401
from app.database.models_snapshots import (  # noqa: F401
    LikedTrackSnapshot,
    PlaylistSnapshot,
    PlaylistTrackSnapshot,
    Snapshot,
)
from app.database.models_spotify_auth import SpotifyAuthToken  # noqa: F401


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # Lightweight sanity check that the DB is writable/readable.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

