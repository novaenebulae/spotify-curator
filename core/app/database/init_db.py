from __future__ import annotations

from sqlalchemy import text

from app.database.engine import get_engine
from app.database.migrate import run_migrations
from app.database.models import Base  # noqa: F401
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
from app.database.models_oauth import OAuthPkceState  # noqa: F401
from app.database.models_playlists import Playlist, PlaylistTrack  # noqa: F401
from app.database.models_runtime import DockerRuntimeCheck  # noqa: F401
from app.database.models_snapshots import (  # noqa: F401
    LikedTrackSnapshot,
    PlaylistSnapshot,
    PlaylistTrackSnapshot,
    Snapshot,
)
from app.database.models_spotify_auth import SpotifyAuthToken  # noqa: F401


def init_db() -> None:
    run_migrations()

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
