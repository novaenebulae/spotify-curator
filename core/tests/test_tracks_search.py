
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.main import create_app
from tests.fixtures.library_seed import seed_library


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "tracks_search.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
    return TestClient(create_app())


def test_search_q_by_title(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"q": "Track One"})
    assert res.status_code == 200
    data = res.json()
    assert data["pagination"]["total"] == 1
    assert data["items"][0]["title"] == "Track One"


def test_search_q_by_artist(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"q": "Artist Y"})
    assert res.status_code == 200
    assert res.json()["pagination"]["total"] == 2


def test_search_q_by_album(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"q": "Alpha"})
    assert res.status_code == 200
    assert res.json()["pagination"]["total"] == 2


def test_filter_isrc(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"isrc": "ISRC222"})
    assert res.status_code == 200
    assert res.json()["pagination"]["total"] == 1


def test_filter_liked(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"liked": True})
    assert res.status_code == 200
    assert res.json()["pagination"]["total"] == 2


def test_filter_playlist(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"spotify_playlist_id": "sp_pl_1"})
    assert res.status_code == 200
    assert res.json()["pagination"]["total"] == 1


def test_filter_in_any_playlist(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"in_any_playlist": True})
    assert res.status_code == 200
    assert res.json()["pagination"]["total"] == 1


def test_filter_duration(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"min_duration_ms": 300000})
    assert res.status_code == 200
    assert res.json()["pagination"]["total"] == 1
    assert res.json()["items"][0]["title"] == "Long Track"


def test_filter_date(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get(
        "/api/v1/tracks",
        params={"liked": True, "added_after": "2026-01-31T00:00:00"},
    )
    assert res.status_code == 200
    assert res.json()["pagination"]["total"] == 2


def test_pagination(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"page": 1, "page_size": 2})
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["pagination"]["total"] == 4
    assert data["pagination"]["total_pages"] == 2


def test_sort_asc_desc(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    asc = client.get("/api/v1/tracks", params={"sort": "duration_ms", "order": "asc"})
    desc = client.get("/api/v1/tracks", params={"sort": "duration_ms", "order": "desc"})
    assert asc.json()["items"][0]["duration_ms"] <= asc.json()["items"][-1]["duration_ms"]
    assert desc.json()["items"][0]["duration_ms"] >= desc.json()["items"][-1]["duration_ms"]


def test_no_duplicate_track_ids(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"in_any_playlist": True, "liked": True})
    assert res.status_code == 200
    ids = [item["track_id"] for item in res.json()["items"]]
    assert len(ids) == len(set(ids))
