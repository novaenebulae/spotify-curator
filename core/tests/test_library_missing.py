from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_library import LikedTrack, SpotifyTrack, Track
from app.database.models_playlists import Playlist, PlaylistTrack
from app.library.diff import (
    STATUS_NULL_PLAYLIST_TRACK,
    STATUS_POSSIBLY_RELINKED,
    STATUS_REMOVED_FROM_LIKED,
    STATUS_UNAVAILABLE_ON_SPOTIFY,
)
from app.library.snapshots import SnapshotService
from app.main import create_app


def _seed_and_snapshots(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "missing.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        for tid, playable, linked in (
            ("s-removed", True, None),
            ("s-unavail", False, None),
            ("s-relink", True, "s-old"),
        ):
            t = Track(name=tid, duration_ms=1, explicit=False, raw_json="{}")
            session.add(t)
            session.flush()
            session.add(
                SpotifyTrack(
                    spotify_track_id=tid,
                    track_id=t.id,
                    spotify_uri=f"spotify:track:{tid}",
                    is_playable=playable,
                    linked_from_spotify_track_id=linked,
                    raw_json="{}",
                )
            )
        session.add(LikedTrack(spotify_track_id="s-removed", added_at=None, raw_json="{}"))
        session.add(Playlist(spotify_playlist_id="p1", spotify_uri="p", name="P", raw_json="{}"))
        session.add(
            PlaylistTrack(
                spotify_playlist_id="p1",
                position=0,
                spotify_track_id=None,
                raw_json="{}",
            )
        )
        session.commit()

    svc = SnapshotService()
    svc.create_snapshot("full")

    with Session(engine) as session:
        session.delete(session.get(LikedTrack, "s-removed"))
        session.add(
            PlaylistTrack(
                spotify_playlist_id="p1",
                position=1,
                spotify_track_id="s-unavail",
                raw_json="{}",
            )
        )
        session.add(
            PlaylistTrack(
                spotify_playlist_id="p1",
                position=2,
                spotify_track_id="s-relink",
                raw_json="{}",
            )
        )
        session.commit()

    svc.create_snapshot("full")
    return TestClient(create_app())


def test_missing_removed_from_liked(tmp_path, monkeypatch) -> None:
    client = _seed_and_snapshots(tmp_path, monkeypatch)
    res = client.get(
        "/api/v1/library/missing-tracks",
        params={"status": STATUS_REMOVED_FROM_LIKED},
    )
    assert res.status_code == 200
    assert res.json()["summary"][STATUS_REMOVED_FROM_LIKED] >= 1


def test_missing_unavailable_on_spotify(tmp_path, monkeypatch) -> None:
    client = _seed_and_snapshots(tmp_path, monkeypatch)
    res = client.get(
        "/api/v1/library/missing-tracks",
        params={"status": STATUS_UNAVAILABLE_ON_SPOTIFY},
    )
    assert res.status_code == 200
    assert res.json()["summary"][STATUS_UNAVAILABLE_ON_SPOTIFY] >= 1


def test_missing_null_playlist_track(tmp_path, monkeypatch) -> None:
    client = _seed_and_snapshots(tmp_path, monkeypatch)
    res = client.get(
        "/api/v1/library/missing-tracks",
        params={"status": STATUS_NULL_PLAYLIST_TRACK},
    )
    assert res.status_code == 200
    assert res.json()["summary"][STATUS_NULL_PLAYLIST_TRACK] >= 1


def test_missing_possibly_relinked(tmp_path, monkeypatch) -> None:
    client = _seed_and_snapshots(tmp_path, monkeypatch)
    res = client.get(
        "/api/v1/library/missing-tracks",
        params={"status": STATUS_POSSIBLY_RELINKED},
    )
    assert res.status_code == 200
    assert res.json()["summary"][STATUS_POSSIBLY_RELINKED] >= 1


def test_missing_summary_by_status(tmp_path, monkeypatch) -> None:
    client = _seed_and_snapshots(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/missing-tracks")
    assert res.status_code == 200
    summary = res.json()["summary"]
    assert sum(summary.values()) >= 1


def test_missing_pagination(tmp_path, monkeypatch) -> None:
    client = _seed_and_snapshots(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/missing-tracks", params={"page_size": 1})
    assert res.status_code == 200
    assert len(res.json()["items"]) <= 1
    assert "pagination" in res.json()
