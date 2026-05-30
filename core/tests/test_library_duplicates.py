from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_library import (
    Album,
    Artist,
    SpotifyTrack,
    Track,
    TrackArtist,
)
from app.main import create_app
from tests.fixtures.library_seed import seed_library


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "duplicates.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
        _add_title_artist_duplicate(session)
    return TestClient(create_app())


def _add_title_artist_duplicate(session: Session) -> None:
    now = datetime(2026, 1, 1)
    artist = session.query(Artist).filter_by(normalized_name="artist x").one()
    album = session.query(Album).first()

    for i, dur in enumerate((180500, 181000)):
        t = Track(
            name="Same Song",
            normalized_title="same song",
            duration_ms=dur,
            explicit=False,
            raw_json="{}",
            created_at=now,
            updated_at=now,
        )
        session.add(t)
        session.flush()
        sp_id = f"sp_dup_{i}"
        session.add(
            SpotifyTrack(
                spotify_track_id=sp_id,
                track_id=t.id,
                album_id=album.id,
                spotify_uri=f"spotify:track:{sp_id}",
                market_status="available",
                raw_json="{}",
            )
        )
        session.add(TrackArtist(track_id=t.id, artist_id=artist.id, position=0))
    session.commit()


def test_duplicate_isrc(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/duplicates", params={"strategy": "isrc"})
    assert res.status_code == 200
    data = res.json()
    assert data["pagination"]["total_groups"] >= 1
    group = data["groups"][0]
    assert group["strategy"] == "isrc"
    assert group["confidence"] == 1.0
    assert group["reason"] == "same_isrc"
    assert len(group["tracks"]) >= 2


def test_duplicate_title_artist(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/duplicates", params={"strategy": "title_artist"})
    assert res.status_code == 200
    assert any(g["reason"] == "same_title_primary_artist" for g in res.json()["groups"])


def test_duplicate_title_artist_duration(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/duplicates", params={"strategy": "title_artist_duration"})
    assert res.status_code == 200
    assert any(g["reason"] == "same_title_artist_similar_duration" for g in res.json()["groups"])


def test_not_duplicate_duration_too_far(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    engine = get_engine()
    with Session(engine) as session:
        t = Track(
            name="Same Song",
            normalized_title="same song",
            duration_ms=300000,
            explicit=False,
            raw_json="{}",
        )
        session.add(t)
        session.flush()
        artist = session.query(Artist).filter_by(normalized_name="artist x").one()
        session.add(
            SpotifyTrack(
                spotify_track_id="sp_far",
                track_id=t.id,
                spotify_uri="spotify:track:sp_far",
                market_status="available",
                raw_json="{}",
            )
        )
        session.add(TrackArtist(track_id=t.id, artist_id=artist.id, position=0))
        session.commit()

    res = client.get("/api/v1/library/duplicates", params={"strategy": "title_artist_duration"})
    groups = res.json()["groups"]
    for g in groups:
        durations = [t["duration_ms"] for t in g["tracks"]]
        assert 300000 not in durations or len(durations) < 2


def test_duplicates_pagination(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/duplicates", params={"strategy": "all", "page_size": 1})
    assert res.status_code == 200
    assert len(res.json()["groups"]) == 1
    assert res.json()["pagination"]["total_groups"] >= 1
