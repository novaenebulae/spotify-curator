from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.audio.pipeline.constants import STAGE_SEGMENT_DOWNLOAD
from app.database.engine import reset_engine
from app.main import create_app


@pytest.fixture
def client(audio_db, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", str(audio_db.url).replace("sqlite:///", "sqlite:///"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    reset_engine()
    return TestClient(create_app())


def test_running_pipeline_job_exposes_live_stages(client) -> None:
    created = client.post(
        "/api/v1/audio/analysis/advanced",
        json={"track_ids": [1], "only_missing": False, "include_tensorflow": False},
    )
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    detail = client.get(f"/api/v1/jobs/{job_id}")
    assert detail.status_code == 200
    job = detail.json()
    assert "stages" in job
    assert STAGE_SEGMENT_DOWNLOAD in job["stages"]
    assert sum(job["stages"][STAGE_SEGMENT_DOWNLOAD].values()) >= 1
    assert "tracks_progress" in job
    assert job["tracks_progress"]["tracks_total"] >= 1
