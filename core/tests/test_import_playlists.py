import httpx
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_playlists import Playlist, PlaylistTrack
from app.jobs.service import JobService
from app.library.import_playlists import import_playlists
from app.spotify.client import SpotifyClient
from app.spotify.token_store import SpotifyTokenStore, StoredToken


class _MemTokenStore(SpotifyTokenStore):
    def __init__(self) -> None:
        self._tok = StoredToken(
            user_id="me",
            access_token="access",
            refresh_token="refresh",
            token_type="Bearer",
            scope="playlist-read-private",
            expires_at=None,
            raw={"access_token": "access", "refresh_token": "refresh"},
        )

    def load(self):  # type: ignore[override]
        return self._tok


def test_import_playlists_handles_null_tracks_and_is_idempotent(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pl.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()

    playlists = [
        {
            "id": "p1",
            "uri": "spotify:playlist:p1",
            "name": "Playlist 1",
            "description": "Desc",
            "owner": {"id": "u1"},
            "public": False,
            "collaborative": False,
            "snapshot_id": "snap1",
        }
    ]

    items = [
        {"added_at": "2020-01-01T00:00:00Z", "added_by": {"id": "u1"}, "track": None},
        {
            "added_at": "2020-01-01T00:00:01Z",
            "added_by": {"id": "u1"},
            "track": {"id": "t1"},
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/me/playlists":
            return httpx.Response(200, json={"items": playlists, "next": None, "total": 1})
        if request.url.path == "/v1/playlists/p1/tracks":
            return httpx.Response(200, json={"items": items, "next": None, "total": 2})
        return httpx.Response(404)

    client = SpotifyClient(
        token_store=_MemTokenStore(),
        transport=httpx.MockTransport(handler),
        sleeper=lambda *_: None,
    )
    jobs = JobService()
    job_id = jobs.create("test_import_playlists")

    res1 = import_playlists(job_id=job_id, jobs=jobs, client=client)
    res2 = import_playlists(job_id=job_id, jobs=jobs, client=client)
    assert res1["playlists"] == 1
    assert res1["items"] == 2
    assert res1["unavailable_items"] == 1
    assert res2["items"] == 2

    engine = get_engine()
    with Session(engine) as session:
        assert session.query(Playlist).count() == 1
        assert session.query(PlaylistTrack).count() == 2
        nulls = (
            session.query(PlaylistTrack)
            .filter(PlaylistTrack.spotify_track_id.is_(None))
            .count()
        )
        assert nulls == 1

