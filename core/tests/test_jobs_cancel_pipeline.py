from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.models_job_items import JobItem
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


def test_cancel_pipeline_via_service_cancels_pending_and_blocked(audio_db) -> None:
    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session)
        session.commit()

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[None, None])],
        include_tensorflow=True,
    )
    items = JobItemService()
    count = items.cancel_pending_for_job(job_id)
    assert count > 0

    with Session(engine) as session:
        non_terminal = list(
            session.scalars(
                select(JobItem).where(
                    JobItem.job_id == job_id,
                    JobItem.status.in_(("pending", "blocked", "rate_limited")),
                )
            )
        )
        assert non_terminal == []


def test_cancel_pipeline_http(client) -> None:
    res = client.post(
        "/api/v1/audio/analysis/advanced",
        json={"track_ids": [1], "only_missing": False, "include_tensorflow": False},
    )
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    cancel = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    engine = get_engine()
    with Session(engine) as session:
        pending = list(
            session.scalars(
                select(JobItem).where(
                    JobItem.job_id == job_id,
                    JobItem.status == "pending",
                )
            )
        )
        blocked = list(
            session.scalars(
                select(JobItem).where(
                    JobItem.job_id == job_id,
                    JobItem.status == "blocked",
                )
            )
        )
        assert pending == []
        assert blocked == []
