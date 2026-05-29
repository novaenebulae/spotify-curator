import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_library import LikedTrack, SpotifyTrack, Track
from app.database.models_playlists import Playlist, PlaylistTrack
from app.library.exports import export_diff, export_liked_tracks, export_playlists, export_snapshot
from app.library.snapshots import SnapshotService
from app.main import create_app


def _seed_library(session: Session) -> None:
    t = Track(name="Track A", duration_ms=1000, explicit=False, raw_json="{}")
    session.add(t)
    session.flush()
    session.add(
        SpotifyTrack(
            spotify_track_id="t1",
            track_id=t.id,
            spotify_uri="spotify:track:t1",
            is_playable=True,
            raw_json="{}",
        )
    )
    session.add(LikedTrack(spotify_track_id="t1", added_at=None, raw_json="{}"))
    session.add(
        Playlist(
            spotify_playlist_id="p1",
            spotify_uri="spotify:playlist:p1",
            name="My Playlist",
            raw_json="{}",
        )
    )
    session.add(
        PlaylistTrack(
            spotify_playlist_id="p1",
            position=0,
            spotify_track_id="t1",
            raw_json="{}",
        )
    )


def test_export_liked_and_playlists(tmp_path, monkeypatch) -> None:
    export_dir = tmp_path / "out"
    db_path = tmp_path / "export.sqlite"
    monkeypatch.setenv("EXPORT_DIR", str(export_dir))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_library(session)
        session.commit()

    liked = export_liked_tracks(fmt="csv")
    assert liked["row_count"] == 1
    assert Path(liked["path"]).exists()

    liked_json = export_liked_tracks(fmt="json")
    data = json.loads(Path(liked_json["path"]).read_text(encoding="utf-8"))
    assert data[0]["spotify_track_id"] == "t1"

    pl = export_playlists(fmt="json")
    playlists = json.loads(Path(pl["path"]).read_text(encoding="utf-8"))
    assert playlists[0]["spotify_playlist_id"] == "p1"
    assert len(playlists[0]["items"]) == 1


def test_export_snapshot_and_diff(tmp_path, monkeypatch) -> None:
    export_dir = tmp_path / "out2"
    db_path = tmp_path / "export2.sqlite"
    monkeypatch.setenv("EXPORT_DIR", str(export_dir))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_library(session)
        session.commit()

    svc = SnapshotService()
    s1 = svc.create_snapshot("full")
    with Session(engine) as session:
        session.delete(session.get(LikedTrack, "t1"))
        session.commit()
    s2 = svc.create_snapshot("full")

    snap = export_snapshot(snapshot_id=s1)
    snap_data = json.loads(Path(snap["path"]).read_text(encoding="utf-8"))
    assert snap_data["snapshot"]["id"] == s1

    diff = export_diff(from_snapshot_id=s1, to_snapshot_id=s2)
    diff_data = json.loads(Path(diff["path"]).read_text(encoding="utf-8"))
    assert diff_data["from_snapshot_id"] == s1
    assert diff_data["to_snapshot_id"] == s2
    assert "liked" in diff_data
    assert diff_data["liked"]["removed"] == ["t1"]


def test_export_api_routes(tmp_path, monkeypatch) -> None:
    export_dir = tmp_path / "out3"
    db_path = tmp_path / "export3.sqlite"
    monkeypatch.setenv("EXPORT_DIR", str(export_dir))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_library(session)
        session.commit()

    client = TestClient(create_app())
    resp = client.post("/api/v1/exports/liked-tracks", json={"format": "json"})
    assert resp.status_code == 200
    assert resp.json()["row_count"] == 1
