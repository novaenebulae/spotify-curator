from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_library import LikedTrack, SpotifyTrack, Track
from app.database.models_playlists import Playlist, PlaylistTrack
from app.library.diff import (
    STATUS_MISSING_FROM_CURRENT_IMPORT,
    STATUS_NULL_PLAYLIST_TRACK,
    STATUS_POSSIBLY_RELINKED,
    STATUS_REMOVED_FROM_LIKED,
    STATUS_UNAVAILABLE_ON_SPOTIFY,
    diff_snapshots,
)
from app.library.snapshots import SnapshotService
from app.main import create_app


def _seed_tracks(session: Session) -> None:
    for tid, playable, linked in (
        ("s-removed", True, None),
        ("s-added", True, None),
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


def test_diff_liked_and_statuses(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "diff.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_tracks(session)
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
    from_id = svc.create_snapshot("full")

    with Session(engine) as session:
        session.delete(session.get(LikedTrack, "s-removed"))
        session.add(LikedTrack(spotify_track_id="s-added", added_at=None, raw_json="{}"))
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

    to_id = svc.create_snapshot("full")

    with Session(engine) as session:
        session.delete(session.get(LikedTrack, "s-added"))
        session.commit()

    result = diff_snapshots(from_id, to_id)

    assert result["liked"]["added"] == ["s-added"]
    assert result["liked"]["removed"] == ["s-removed"]
    assert result["summary"]["liked"]["added_count"] == 1
    assert result["summary"]["liked"]["removed_count"] == 1

    statuses = {s["status"] for s in result["tracks"]["statuses"]}
    assert STATUS_REMOVED_FROM_LIKED in statuses
    assert STATUS_MISSING_FROM_CURRENT_IMPORT in statuses
    assert STATUS_NULL_PLAYLIST_TRACK in statuses
    assert STATUS_UNAVAILABLE_ON_SPOTIFY in statuses
    assert STATUS_POSSIBLY_RELINKED in statuses


def test_diff_api_endpoint(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "diff_api.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_tracks(session)
        session.add(LikedTrack(spotify_track_id="s-removed", added_at=None, raw_json="{}"))
        session.commit()

    svc = SnapshotService()
    from_id = svc.create_snapshot("liked")
    with Session(engine) as session:
        session.delete(session.get(LikedTrack, "s-removed"))
        session.add(LikedTrack(spotify_track_id="s-added", added_at=None, raw_json="{}"))
        session.commit()
    to_id = svc.create_snapshot("liked")

    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/library/snapshots/diff",
        json={"from_snapshot_id": from_id, "to_snapshot_id": to_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["from_snapshot_id"] == from_id
    assert body["to_snapshot_id"] == to_id
    assert "s-added" in body["liked"]["added"]
    assert "s-removed" in body["liked"]["removed"]


def test_diff_missing_snapshot(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "diff_missing.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()

    client = TestClient(create_app())
    resp = client.post(
        "/api/v1/library/snapshots/diff",
        json={"from_snapshot_id": "nope", "to_snapshot_id": "nope"},
    )
    assert resp.status_code == 404
