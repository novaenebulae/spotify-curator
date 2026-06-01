import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.previews.deezer_client import DeezerClient


def test_preview_coverage_empty(audio_db, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", str(audio_db.url))
    from app.database.engine import reset_engine

    reset_engine()
    client = TestClient(app)
    resp = client.get("/api/v1/previews/coverage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["track_count"] >= 1


def test_get_track_preview_not_found(audio_db, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", str(audio_db.url))
    from app.database.engine import reset_engine

    reset_engine()
    client = TestClient(app)
    resp = client.get("/api/v1/tracks/1/preview")
    assert resp.status_code == 200
    assert resp.json()["is_available"] is False
