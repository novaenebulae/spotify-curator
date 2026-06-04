from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.pipeline.constants import STAGE_SEGMENT_DOWNLOAD
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.models_job_items import JobEvent, JobItem
from app.database.models_library import Track
from app.jobs.items.service import JobItemService
from app.main import create_app


@pytest.fixture
def client(audio_db, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", str(audio_db.url).replace("sqlite:///", "sqlite:///"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    reset_engine()
    return TestClient(create_app())


def _seed_track(session: Session, track_id: int = 1) -> None:
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    if session.get(Track, track_id) is None:
        session.add(
            Track(
                id=track_id,
                name="t",
                normalized_title="t",
                duration_ms=60_000,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()


def test_events_api_lists_stage_created(audio_db) -> None:
    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session)
        session.commit()

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[None])],
        include_tensorflow=False,
    )

    with Session(engine) as session:
        events = list(
            session.scalars(
                select(JobEvent)
                .where(JobEvent.job_id == job_id)
                .order_by(JobEvent.created_at.desc())
            )
        )
    types = {e.event_type for e in events}
    assert "stage_created" in types


def test_events_http_route(client) -> None:
    res = client.post(
        "/api/v1/audio/analysis/advanced",
        json={
            "track_ids": [1],
            "only_missing": False,
            "include_tensorflow": False,
        },
    )
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    events_res = client.get(f"/api/v1/jobs/{job_id}/events?limit=20")
    assert events_res.status_code == 200
    body = events_res.json()
    assert body["job_id"] == job_id
    assert body["count"] >= 1
    event_types = {e["event_type"] for e in body["events"]}
    assert "stage_created" in event_types

    filtered = client.get(
        f"/api/v1/jobs/{job_id}/events?event_type=stage_created&limit=5"
    )
    assert filtered.status_code == 200
    assert all(e["event_type"] == "stage_created" for e in filtered.json()["events"])


def test_stage_started_after_reserve(audio_db) -> None:
    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session)
        session.commit()

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[None])],
        include_tensorflow=False,
    )
    items = JobItemService()
    reserved = items.reserve_next(
        worker_id="dl-1", worker_type="audio_downloader"
    )
    assert reserved is not None
    assert reserved.stage_name == STAGE_SEGMENT_DOWNLOAD

    with Session(engine) as session:
        started = list(
            session.scalars(
                select(JobEvent).where(
                    JobEvent.job_id == job_id,
                    JobEvent.event_type == "stage_started",
                )
            )
        )
    assert len(started) >= 1
    ctx = __import__("json").loads(started[0].context_json)
    assert ctx.get("stage_name") == STAGE_SEGMENT_DOWNLOAD


def test_cancel_cancels_blocked_items(client) -> None:
    res = client.post(
        "/api/v1/audio/analysis/advanced",
        json={
            "track_ids": [1],
            "only_missing": False,
            "include_tensorflow": True,
        },
    )
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    engine = get_engine()
    with Session(engine) as session:
        blocked = list(
            session.scalars(
                select(JobItem).where(
                    JobItem.job_id == job_id,
                    JobItem.status == "blocked",
                )
            )
        )
        assert len(blocked) >= 1

    cancel_res = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 200

    with Session(engine) as session:
        still_blocked = list(
            session.scalars(
                select(JobItem).where(
                    JobItem.job_id == job_id,
                    JobItem.status == "blocked",
                )
            )
        )
        assert still_blocked == []
        cancelled = list(
            session.scalars(
                select(JobEvent).where(
                    JobEvent.job_id == job_id,
                    JobEvent.event_type == "cancelled",
                )
            )
        )
        assert len(cancelled) >= 1

    job_res = client.get(f"/api/v1/jobs/{job_id}")
    assert job_res.json()["status"] == "cancelled"
