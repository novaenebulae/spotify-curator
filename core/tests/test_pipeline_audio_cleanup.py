from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.essentia_parser import parse_essentia_json_file, parsed_segment_to_storage_dict
from app.audio.pipeline.audio_cleanup import PipelineAudioCleanupService
from app.audio.pipeline.constants import (
    STAGE_AUDIO_CLEANUP,
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_FEATURE_AGGREGATION,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_audio import TrackSegment
from app.database.models_job_items import JobEvent
from app.database.models_library import Track
from app.jobs.items.service import JobItemService
from app.settings import config


def _patch_cache(monkeypatch, tmp_path):
    cache_root = tmp_path / "cache"
    monkeypatch.setattr(config.settings, "cache_dir", str(cache_root))
    return cache_root


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


def test_pipeline_cleanup_deletes_segment_and_emits_event(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipe_cleanup.sqlite"
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_sample.json"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setattr(config.settings, "audio_keep_segments_after_analysis", False)
    cache_root = _patch_cache(monkeypatch, tmp_path)
    reset_engine()
    init_db()

    parsed = parse_essentia_json_file(str(fixture))
    storage = json.dumps(parsed_segment_to_storage_dict(parsed))
    engine = get_engine()
    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=False,
    )
    rel = f"audio_segments/1/{job_id}/seg.wav"
    with Session(engine) as session:
        _seed_track(session)
        session.add(
            TrackSegment(
                id=10,
                track_id=1,
                start_seconds=0,
                end_seconds=15,
                duration_seconds=15,
                segment_type="A",
                source="test",
                temporary_path=rel,
                features_json=storage,
                created_at=datetime.now(tz=UTC).replace(tzinfo=None),
            )
        )
        session.commit()
    wav = cache_root / "audio_segments" / "1" / job_id / "seg.wav"
    wav.parent.mkdir(parents=True, exist_ok=True)
    wav.write_bytes(b"\x00\x01")
    items = JobItemService()
    for row in items.list_items(job_id):
        if row["stage_name"] in (STAGE_SEGMENT_DOWNLOAD, STAGE_ESSENTIA_LOWLEVEL):
            items.mark_success(row["id"])

    agg = next(
        i for i in items.list_items(job_id) if i["stage_name"] == STAGE_FEATURE_AGGREGATION
    )
    assert agg["status"] == "success"

    cleanup_item = next(
        i for i in items.list_items(job_id) if i["stage_name"] == STAGE_AUDIO_CLEANUP
    )
    if cleanup_item["status"] == "pending":
        cleanup_svc = PipelineAudioCleanupService(items=items)
        assert cleanup_svc.try_run_pending_for_job(job_id) == 1
        cleanup_item = next(
            i for i in items.list_items(job_id) if i["stage_name"] == STAGE_AUDIO_CLEANUP
        )
    assert cleanup_item["status"] == "success"
    assert cleanup_item["result"].get("deleted_files", 0) >= 1

    with Session(engine) as session:
        seg = session.get(TrackSegment, 10)
        assert seg is not None
        assert seg.deleted_at is not None
        events = list(
            session.scalars(
                select(JobEvent).where(
                    JobEvent.job_id == job_id,
                    JobEvent.event_type == "cleanup_done",
                )
            )
        )
        assert len(events) >= 1
