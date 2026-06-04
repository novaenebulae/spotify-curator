from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.handoff import PipelineSegmentHandoffService
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.audio.provider import PlannedSegment
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.database.models_library import Track
from app.jobs.items.service import JobItemService
from app.settings.config import settings
from app.workers.audio_downloader_worker import AudioDownloaderWorker


def _seed_track(session: Session, track_id: int = 1) -> None:
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    if session.get(Track, track_id) is None:
        session.add(
            Track(
                id=track_id,
                name=f"Track {track_id}",
                normalized_title=f"track {track_id}",
                duration_ms=180_000,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()


def _planned_a() -> dict:
    return {
        "segment_type": "A",
        "start_seconds": 10.0,
        "end_seconds": 25.0,
        "duration_seconds": 15.0,
        "strategy": "abc_default",
        "source": "youtube",
    }


def _planned_b() -> dict:
    return {
        "segment_type": "B",
        "start_seconds": 45.0,
        "end_seconds": 60.0,
        "duration_seconds": 15.0,
        "strategy": "abc_default",
        "source": "youtube",
    }


def test_handoff_unblocks_analysis_before_all_downloads_done(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "handoff.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [
            TrackSegmentPlan(
                track_id=1,
                segment_ids=[None, None],
                planned_segments=(_planned_a(), _planned_b()),
            ),
        ],
        include_tensorflow=False,
    )

    items = JobItemService().list_items(job_id, limit=50)
    downloads = [i for i in items if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD]
    assert len(downloads) == 2

    handoff = PipelineSegmentHandoffService(orchestrator=orch)
    with Session(engine) as session:
        handoff.on_segment_ready(
            session,
            job_id=job_id,
            track_id=1,
            segment_id=101,
            download_item_id=downloads[0]["id"],
            segment_index=0,
        )
        session.commit()
    handoff.complete_segment_handoff(job_id)

    refreshed = JobItemService().list_items(job_id, limit=50)
    ll_items = [i for i in refreshed if i["stage_name"] == STAGE_ESSENTIA_LOWLEVEL]
    ll_slot0 = next(i for i in ll_items if i["depends_on_item_id"] == downloads[0]["id"])
    ll_slot1 = next(i for i in ll_items if i["depends_on_item_id"] == downloads[1]["id"])
    assert ll_slot0["status"] == "pending"
    assert ll_slot0["segment_id"] == 101
    assert ll_slot1["status"] == "blocked"
    assert downloads[1]["status"] in ("pending", "running")


def test_pipeline_downloader_handoff_with_stub_provider(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_dl.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("AUDIO_USE_TEST_PROVIDER", "1")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [
            TrackSegmentPlan(
                track_id=1,
                segment_ids=[None],
                planned_segments=(_planned_a(),),
            ),
        ],
        include_tensorflow=False,
    )

    items = JobItemService()
    reserved = items.reserve_next(worker_id="dl-test", worker_type="audio_downloader")
    assert reserved is not None
    assert reserved.job_id == job_id

    worker = AudioDownloaderWorker(use_test_provider=True)
    worker.process_item(reserved)

    all_items = items.list_items(job_id, limit=20)
    ll = next(i for i in all_items if i["stage_name"] == STAGE_ESSENTIA_LOWLEVEL)
    assert ll["status"] == "pending"
    assert ll["segment_id"] is not None


def test_legacy_mode_skips_pipeline_reservation(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "legacy_mode.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("ANALYSIS_PIPELINE_MODE", "legacy")
    reset_engine()
    init_db()

    from app.settings.config import Settings

    monkeypatch.setattr(
        "app.jobs.items.service.settings",
        Settings(analysis_pipeline_mode="legacy"),
    )

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[None], planned_segments=(_planned_a(),))],
        include_tensorflow=False,
    )

    items = JobItemService()
    reserved = items.reserve_next(worker_id="dl-test", worker_type="audio_downloader")
    assert reserved is None

    download_items = [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD]
    assert len(download_items) == 1
    assert download_items[0]["status"] == "pending"
