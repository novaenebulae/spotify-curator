from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.cleanup import AudioCleanupService
from app.audio.pipeline.constants import STAGE_ESSENTIA_LOWLEVEL
from app.audio.pipeline.consumers import segment_cleanup_allowed
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_audio import TrackSegment
from app.database.models_library import Track
from app.jobs.items.service import JobItemService


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


def test_cleanup_blocked_while_consumer_pending(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "cleanup_gate.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.add(
            TrackSegment(
                track_id=1,
                start_seconds=0,
                end_seconds=15,
                duration_seconds=15,
                segment_type="A",
                source="test",
                temporary_path="cache/audio_segments/1/fake.wav",
                created_at=datetime.now(tz=UTC).replace(tzinfo=None),
            )
        )
        session.flush()
        segment_id = 1
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[segment_id])],
        include_tensorflow=False,
    )

    with Session(engine) as session:
        assert not segment_cleanup_allowed(session, segment_id=segment_id)

    items = JobItemService()
    ll = next(
        i
        for i in items.list_items(job_id, limit=20)
        if i["stage_name"] == STAGE_ESSENTIA_LOWLEVEL
    )
    download = next(
        i for i in items.list_items(job_id, limit=20) if i["stage_name"] == "segment_download"
    )
    items.mark_success(download["id"])

    with Session(engine) as session:
        assert not segment_cleanup_allowed(session, segment_id=segment_id)

    items.mark_success(ll["id"])

    with Session(engine) as session:
        assert segment_cleanup_allowed(session, segment_id=segment_id)
