from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_library import LikedTrack, SpotifyTrack, Track
from app.database.models_playlists import Playlist, PlaylistTrack
from app.library.snapshots import SnapshotService


def test_create_full_snapshot(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "snap.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        t = Track(name="t", duration_ms=1, explicit=False, raw_json="{}")
        session.add(t)
        session.flush()
        session.add(
            SpotifyTrack(
                spotify_track_id="s1",
                track_id=t.id,
                spotify_uri="u",
                raw_json="{}",
            )
        )
        session.add(LikedTrack(spotify_track_id="s1", added_at=None, raw_json="{}"))
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
    sid = svc.create_snapshot("full")
    s = svc.get_snapshot(sid)
    assert s is not None
    assert s["type"] == "full"
    assert s["track_count"] == 1
    assert s["playlist_count"] == 1

