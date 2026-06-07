from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database.engine import reset_engine
from app.jobs.items.service import ReservedJobItem
from app.main import create_app
from app.workers.essentia_tensorflow_worker import EssentiaTensorflowWorker
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


def test_tensorflow_worker_pulses_heartbeat_during_long_inference(
    audio_db, monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("DATABASE_URL", str(audio_db.url).replace("sqlite:///", "sqlite:///"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("JOB_WORKER_HEARTBEAT_INTERVAL_SECONDS", "1")
    reset_engine()
    from app.settings.config import settings

    monkeypatch.setattr(settings, "job_worker_heartbeat_interval_seconds", 1)

    heartbeat = MagicMock()
    worker = EssentiaTensorflowWorker()
    worker._heartbeat = heartbeat
    item = ReservedJobItem(
        id="item_tf_1",
        job_id="job_pipeline_1",
        item_type="pipeline_stage",
        track_id=1,
        segment_id=1,
        input_json={},
        attempt_count=0,
        stage_name="essentia_tensorflow_embeddings",
    )

    def _slow_batch(_item: ReservedJobItem) -> bool:
        time.sleep(3.5)
        return False

    worker._process_item_for_batch = _slow_batch  # type: ignore[method-assign]
    worker._process_pipeline_item_with_heartbeat(item)

    running_updates = [
        call.kwargs.get("status")
        for call in heartbeat.register_or_update.call_args_list
        if call.kwargs.get("status") == "running"
    ]
    assert len(running_updates) >= 3
