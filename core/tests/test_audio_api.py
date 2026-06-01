from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(audio_db, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", str(audio_db.url).replace("sqlite:///", "sqlite:///"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CACHE_DIR", os.environ.get("CACHE_DIR", "/tmp/cache"))
    from app.database.engine import reset_engine

    reset_engine()
    return TestClient(create_app())


def test_plan_segments(client) -> None:
    res = client.post(
        "/api/v1/audio/segments/plan",
        json={"track_id": 1, "strategy": "abc_default", "segment_duration_seconds": 15},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["track_id"] == 1
    assert len(body["segments"]) >= 1
    for s in body["segments"]:
        assert s["duration_seconds"] <= 30


def test_download_job_created(client) -> None:
    res = client.post(
        "/api/v1/audio/segments/download",
        json={"track_ids": [1], "strategy": "abc_default", "only_missing": True, "limit": 1},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["job_id"]
    assert body["status"] in ("pending", "queued")

    items = client.get(f"/api/v1/jobs/{body['job_id']}/items")
    assert items.status_code == 200
    assert len(items.json()["items"]) == 1


def test_workers_endpoint(client) -> None:
    res = client.get("/api/v1/workers")
    assert res.status_code == 200
    assert "workers" in res.json()
