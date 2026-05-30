from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_library import (
    Album,
    Artist,
    ExternalId,
    SpotifyTrack,
    Track,
    TrackArtist,
)
from app.library.duplicates_present import dedupe_tracks_for_display, present_duplicate_group
from app.main import create_app
from tests.fixtures.library_seed import seed_library


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "dup.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
    return TestClient(create_app())


def test_dedupe_same_spotify_track_id() -> None:
    raw = [
        {"track_id": 1, "spotify_track_id": "sp_same", "title": "A", "artist_names": ["X"]},
        {"track_id": 2, "spotify_track_id": "sp_same", "title": "A", "artist_names": ["X"]},
        {"track_id": 3, "spotify_track_id": "sp_same", "title": "A", "artist_names": ["X"]},
    ]
    unique = dedupe_tracks_for_display(raw)
    assert len(unique) == 1
    assert unique[0]["occurrence_count"] == 3


def test_present_group_repeated_occurrence() -> None:
    raw = [
        {"track_id": 1, "spotify_track_id": "sp1", "title": "T", "isrc": "ISRC1"},
        {"track_id": 2, "spotify_track_id": "sp1", "title": "T", "isrc": "ISRC1"},
    ]
    group = present_duplicate_group(
        group_id="g1",
        strategy="isrc",
        confidence=1.0,
        reason="same_isrc",
        raw_tracks=raw,
    )
    assert group["unique_track_count"] == 1
    assert group["occurrence_count"] == 2
    assert group["is_repeated_occurrence"] is True
    assert group["reason_label"] == "Same ISRC"


def test_duplicates_api_has_cover_and_labels(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/duplicates", params={"strategy": "isrc"})
    assert res.status_code == 200
    data = res.json()
    if data["groups"]:
        group = data["groups"][0]
        assert "reason_label" in group
        assert "unique_track_count" in group
        if group["tracks"]:
            assert "cover_image_url" in group["tracks"][0] or group["tracks"][0].get("album_name")


def test_duplicates_isrc_two_unique_tracks(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "dup2.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
        album = Album(name="Dup Album", normalized_name="dup album", raw_json="{}")
        artist = Artist(name="Dup Artist", normalized_name="dup artist", raw_json="{}")
        session.add_all([album, artist])
        session.flush()
        for i, sp_id in enumerate(["sp_dup_a", "sp_dup_b"], start=10):
            t = Track(
                name=f"Dup Track {i}",
                normalized_title=f"dup track {i}",
                duration_ms=200000,
                raw_json="{}",
            )
            session.add(t)
            session.flush()
            session.add(
                SpotifyTrack(
                    spotify_track_id=sp_id,
                    track_id=t.id,
                    spotify_uri=f"spotify:track:{sp_id}",
                    album_id=album.id,
                    raw_json="{}",
                )
            )
            session.add(TrackArtist(track_id=t.id, artist_id=artist.id, position=0))
            session.add(
                ExternalId(
                    track_id=t.id,
                    id_type="isrc",
                    id_value="SHARED_ISRC",
                    source="spotify",
                    external_type="isrc",
                )
            )
        session.commit()

    client = TestClient(create_app())
    res = client.get("/api/v1/library/duplicates", params={"strategy": "isrc"})
    assert res.status_code == 200
    groups = [g for g in res.json()["groups"] if g.get("isrc") == "SHARED_ISRC"]
    assert groups
    assert groups[0]["unique_track_count"] >= 2
