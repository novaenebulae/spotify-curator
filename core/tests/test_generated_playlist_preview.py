from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.main import create_app
from app.playlists.presets import load_presets
from tests.fixtures.library_seed import seed_library
from tests.test_track_features_api import _seed_reccobeats


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "preview.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        ids = seed_library(session)
        for sp_key in ("sp_t1", "sp_t2"):
            _seed_reccobeats(session, int(ids[sp_key]))
        session.commit()
    return TestClient(create_app())


def test_preview_persists(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    preset = next(p for p in load_presets() if p["id"] == "dark_intense")
    rule = preset["rule"]
    resp = client.post("/api/v1/generated-playlists/preview", json={"rule": rule})
    assert resp.status_code == 200
    body = resp.json()
    assert "generated_playlist_id" in body
    assert body["dry_run"] is True
    assert "summary" in body

    gp_id = body["generated_playlist_id"]
    detail = client.get(f"/api/v1/generated-playlists/{gp_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == gp_id
