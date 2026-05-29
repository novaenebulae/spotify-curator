import httpx

from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_library import LikedTrack, SpotifyTrack
from app.jobs.service import JobService
from app.library.import_liked import import_liked_tracks
from app.spotify.client import SpotifyClient
from app.spotify.token_store import SpotifyTokenStore, StoredToken


class _MemTokenStore(SpotifyTokenStore):
    def __init__(self) -> None:
        self._tok = StoredToken(
            user_id="user1",
            access_token="access",
            refresh_token="refresh",
            token_type="Bearer",
            scope="user-library-read",
            expires_at=None,
            raw={"access_token": "access"},
        )

    def load(self):  # type: ignore[override]
        return self._tok


def test_import_liked_sets_is_current_and_market_status(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "enriched.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    saved_items = [
        {
            "added_at": "2020-01-01T00:00:00Z",
            "track": {
                "id": "t1",
                "uri": "spotify:track:t1",
                "name": "Track 1",
                "duration_ms": 123000,
                "explicit": False,
                "popularity": 10,
                "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
                "external_ids": {"isrc": "ISRC1"},
                "album": {"id": "a1", "name": "Album 1"},
                "artists": [{"id": "ar1", "name": "Artist 1"}],
                "is_playable": True,
                "available_markets": ["FR"],
            },
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/me/tracks":
            return httpx.Response(200, json={"items": saved_items, "next": None, "total": 1})
        return httpx.Response(404)

    client = SpotifyClient(
        token_store=_MemTokenStore(),
        transport=httpx.MockTransport(handler),
        sleeper=lambda *_: None,
    )
    jobs = JobService()
    job_id = jobs.create("test_import_liked")
    import_liked_tracks(job_id=job_id, jobs=jobs, client=client)

    from sqlalchemy.orm import Session

    engine = get_engine()
    with Session(engine) as session:
        liked = session.get(LikedTrack, "t1")
        assert liked is not None
        assert liked.is_current is True
        assert liked.first_seen_at is not None
        assert liked.last_seen_at is not None

        sp = session.get(SpotifyTrack, "t1")
        assert sp is not None
        assert sp.market_status == "available"

    import_liked_tracks(job_id=job_id, jobs=jobs, client=client)
    with Session(engine) as session:
        from sqlalchemy import func, select

        stale = session.execute(
            select(func.count()).select_from(LikedTrack).where(LikedTrack.is_current.is_(False))
        ).scalar_one()
        assert stale == 0
