from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_spotify_auth import SpotifyAuthToken
from app.main import create_app
from tests.fixtures.library_seed import seed_library


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "actions.sqlite"
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
    return TestClient(create_app())


def _liked_track_id(client: TestClient) -> int:
    res = client.get("/api/v1/tracks", params={"liked": True, "page_size": 1})
    return res.json()["items"][0]["track_id"]


def test_dry_run_unlike_tracks(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    tid = _liked_track_id(client)
    res = client.post(
        "/api/v1/library/actions/dry-run",
        json={"action_type": "unlike_tracks", "track_ids": [tid]},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["dry_run"] is True
    assert data["spotify_applied"] is False
    assert data["affected_count"] == 1
    assert any(w["code"] == "WRITE_SCOPE_MISSING" for w in data["warnings"])


def test_dry_run_restore_liked_tracks(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/tracks", params={"liked": False, "page_size": 1})
    tid = res.json()["items"][0]["track_id"]
    res = client.post(
        "/api/v1/library/actions/dry-run",
        json={"action_type": "restore_liked_tracks", "track_ids": [tid]},
    )
    assert res.status_code == 200
    assert res.json()["affected_count"] == 1


def test_dry_run_create_backup_playlist(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    tid = _liked_track_id(client)
    res = client.post(
        "/api/v1/library/actions/dry-run",
        json={
            "action_type": "create_backup_playlist",
            "track_ids": [tid],
            "options": {"backup_playlist_name": "Backup Test"},
        },
    )
    assert res.status_code == 200
    assert res.json()["action_type"] == "create_backup_playlist"


def test_dry_run_filter_based(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.post(
        "/api/v1/library/actions/dry-run",
        json={"action_type": "unlike_tracks", "filter": {"liked": True}},
    )
    assert res.status_code == 200
    assert res.json()["affected_count"] == 2


def test_dry_run_action_too_large(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.post(
        "/api/v1/library/actions/dry-run",
        json={"action_type": "unlike_tracks", "track_ids": list(range(1, 502))},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_dry_run_creates_library_action_row(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    tid = _liked_track_id(client)
    res = client.post(
        "/api/v1/library/actions/dry-run",
        json={"action_type": "unlike_tracks", "track_ids": [tid]},
    )
    action_id = res.json()["action_id"]
    detail = client.get(f"/api/v1/library/actions/{action_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "previewed"
