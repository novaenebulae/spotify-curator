from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.main import create_app
from app.playlists.presets import load_presets
from tests.fixtures.library_seed import seed_library


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "rules_api.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
    return TestClient(create_app())


def test_playlist_rules_crud(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    rule = load_presets()[0]["rule"]

    created = client.post(
        "/api/v1/playlist-rules",
        json={"name": "Test Rule", "rule": rule},
    )
    assert created.status_code == 200
    rule_id = created.json()["id"]

    listed = client.get("/api/v1/playlist-rules")
    assert listed.status_code == 200
    assert any(i["id"] == rule_id for i in listed.json()["items"])

    got = client.get(f"/api/v1/playlist-rules/{rule_id}")
    assert got.status_code == 200

    deleted = client.delete(f"/api/v1/playlist-rules/{rule_id}")
    assert deleted.status_code == 200

    listed_disabled = client.get("/api/v1/playlist-rules?enabled_only=true")
    assert not any(i["id"] == rule_id for i in listed_disabled.json()["items"])


def test_validate_endpoint(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    resp = client.post(
        "/api/v1/playlist-rules/validate",
        json={"rule": load_presets()[0]["rule"]},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True
