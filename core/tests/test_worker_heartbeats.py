from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database.engine import reset_engine
from app.main import create_app
from app.workers.heartbeat import WorkerHeartbeatService


@pytest.fixture
def client(audio_db, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", str(audio_db.url).replace("sqlite:///", "sqlite:///"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    reset_engine()
    return TestClient(create_app())


def test_register_heartbeat_visible_on_workers_api(client) -> None:
    svc = WorkerHeartbeatService()
    svc.register_or_update(
        worker_id="test-worker-1",
        worker_type="audio_downloader",
        status="idle",
        metadata={"stage_name": "segment_download"},
    )

    res = client.get("/api/v1/workers")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] >= 1
    worker = next(w for w in body["workers"] if w["worker_id"] == "test-worker-1")
    assert worker["worker_type"] == "audio_downloader"
    assert worker["status"] == "idle"
    assert worker["metadata"].get("stage_name") == "segment_download"

    filtered = client.get("/api/v1/workers?worker_type=audio_downloader")
    assert filtered.status_code == 200
    assert any(w["worker_id"] == "test-worker-1" for w in filtered.json()["workers"])
