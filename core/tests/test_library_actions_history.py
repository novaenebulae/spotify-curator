from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_spotify_auth import SpotifyAuthToken
from app.main import create_app
from tests.fixtures.library_seed import seed_library


def _client_with_action(tmp_path, monkeypatch) -> tuple[TestClient, int]:
    db_path = tmp_path / "actions_history.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
        session.add(
            SpotifyAuthToken(
                user_id="u1",
                access_token="tok",
                refresh_token="ref",
                scope="user-library-read",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        session.commit()
    client = TestClient(create_app())
    tid = client.get("/api/v1/tracks", params={"liked": True, "page_size": 1}).json()["items"][0][
        "track_id"
    ]
    action_id = client.post(
        "/api/v1/library/actions/dry-run",
        json={"action_type": "unlike_tracks", "track_ids": [tid]},
    ).json()["action_id"]
    return client, action_id


def test_list_actions(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_action(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/actions")
    assert res.status_code == 200
    assert res.json()["pagination"]["total"] >= 1


def test_filter_action_type(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_action(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/actions", params={"action_type": "unlike_tracks"})
    assert res.status_code == 200
    assert all(i["action_type"] == "unlike_tracks" for i in res.json()["items"])


def test_filter_dry_run(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_action(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/actions", params={"dry_run": True})
    assert res.status_code == 200
    assert all(i["dry_run"] is True for i in res.json()["items"])


def test_detail_action(tmp_path, monkeypatch) -> None:
    client, action_id = _client_with_action(tmp_path, monkeypatch)
    res = client.get(f"/api/v1/library/actions/{action_id}")
    assert res.status_code == 200
    data = res.json()
    assert "result" in data
    assert "warnings" in data
    assert data["dry_run"] is True


def test_detail_not_found(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_action(tmp_path, monkeypatch)
    res = client.get("/api/v1/library/actions/99999")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"
