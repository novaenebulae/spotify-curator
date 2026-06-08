from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_FEATURE_AGGREGATION,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.database.engine import reset_engine
from app.database.models_jobs import Job
from app.main import create_app


@pytest.fixture
def client(audio_db, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", str(audio_db.url).replace("sqlite:///", "sqlite:///"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    reset_engine()
    return TestClient(create_app())


def test_advanced_analysis_creates_pipeline_job(client) -> None:
    res = client.post(
        "/api/v1/audio/analysis/advanced",
        json={
            "track_ids": [1],
            "strategy": "abc_default",
            "only_missing": False,
            "include_tensorflow": False,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["job_id"]
    assert body["status"] in ("pending", "queued")

    job_res = client.get(f"/api/v1/jobs/{body['job_id']}")
    assert job_res.status_code == 200
    job = job_res.json()
    assert job["job_type"] == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE
    assert "stages" in job
    assert job["stages"][STAGE_SEGMENT_DOWNLOAD]["pending"] >= 1

    items = client.get(f"/api/v1/jobs/{body['job_id']}/items?limit=200")
    stages = {i["stage_name"] for i in items.json()["items"]}
    assert STAGE_SEGMENT_DOWNLOAD in stages
    assert STAGE_ESSENTIA_LOWLEVEL in stages
    assert STAGE_FEATURE_AGGREGATION in stages


def test_advanced_analysis_job_already_running(client) -> None:
    first = client.post(
        "/api/v1/audio/analysis/advanced",
        json={"track_ids": [1], "only_missing": False, "include_tensorflow": False},
    )
    assert first.status_code == 200
    job_id = first.json()["job_id"]

    from app.database.engine import get_engine

    engine = get_engine()
    with Session(engine) as session:
        row = session.get(Job, job_id)
        assert row is not None
        row.status = "running"
        session.commit()

    second = client.post(
        "/api/v1/audio/analysis/advanced",
        json={"track_ids": [1], "only_missing": False},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "JOB_ALREADY_RUNNING"


def test_require_real_tensorflow_blocks_when_models_missing(client) -> None:
    with patch("app.audio.advanced_analysis_job_service.ModelManager") as mock_mgr:
        instance = mock_mgr.return_value
        instance.get_status.return_value = {
            "summary": {"real_inference_ready": False},
            "profiles": [{"name": "phase6-recommended", "status": "missing"}],
            "models": [],
        }
        res = client.post(
            "/api/v1/audio/analysis/advanced",
            json={
                "track_ids": [1],
                "require_real_tensorflow": True,
                "model_profile": "phase6-recommended",
            },
        )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "MODEL_MISSING"


def test_advanced_analysis_hybrid_survives_ytdlp_missing(client) -> None:
    with patch("app.audio.ytdlp_provider.YtDlpSegmentProvider.resolve") as mock_resolve:
        from app.audio.errors import YtDlpError

        mock_resolve.side_effect = YtDlpError("YTDLP_NOT_FOUND", "yt-dlp binary not found on PATH")
        res = client.post(
            "/api/v1/audio/analysis/advanced",
            json={
                "track_ids": [1],
                "strategy": "hybrid_deezer_youtube_representative",
                "only_missing": False,
                "include_tensorflow": False,
            },
        )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "NO_TRACKS"
