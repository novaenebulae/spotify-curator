from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.audio.pipeline.constants import JOB_TYPE_AUDIO_ANALYSIS_PIPELINE
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.database.models_library import Track
from app.jobs.items.service import JobItemService


def test_reconcile_finishes_stuck_running_parent(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "reconcile.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        session.add(
            Track(
                id=1,
                name="t",
                normalized_title="t",
                duration_ms=60_000,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=False,
        include_tensorflow=False,
    )
    items = JobItemService()
    for row in items.list_items(job_id):
        items.mark_success(row["id"])

    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        job.status = "running"
        session.commit()

    finished = items.reconcile_audio_analysis_pipeline_jobs()
    assert job_id in finished

    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.status == "succeeded"

    job_id2 = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[11])],
        include_lowlevel=False,
        include_tensorflow=False,
    )
    assert job_id2 != job_id


def test_release_stale_locks_includes_pipeline_download_stage(
    tmp_path, monkeypatch
) -> None:
    db_path = tmp_path / "stale_dl.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        session.add(
            Track(
                id=1,
                name="t",
                normalized_title="t",
                duration_ms=60_000,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=False,
        include_tensorflow=False,
    )
    items = JobItemService()
    download = next(
        i for i in items.list_items(job_id) if i["stage_name"] == "segment_download"
    )
    stale_at = datetime.now(tz=UTC).replace(tzinfo=None) - timedelta(seconds=3600)
    with Session(engine) as session:
        row = session.get(JobItem, download["id"])
        assert row is not None
        row.status = "running"
        row.locked_by = "dead-worker"
        row.locked_at = stale_at
        session.commit()

    released = items.release_stale_locks(worker_type="audio_downloader")
    assert released >= 1

    with Session(engine) as session:
        row = session.get(JobItem, download["id"])
        assert row is not None
        assert row.status == "pending"
        assert row.locked_by is None
