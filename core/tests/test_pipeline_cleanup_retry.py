from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.audio.pipeline.audio_cleanup import PipelineAudioCleanupService
from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_AUDIO_CLEANUP,
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.ticker import AnalysisPipelineTicker
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_jobs import Job
from app.database.models_library import Track
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService


def test_cleanup_retryable_triggers_refresh(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "cleanup_retry.sqlite"
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

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create(JOB_TYPE_AUDIO_ANALYSIS_PIPELINE)
    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        job.status = "running"
        job.result_json = json.dumps({"track_count": 1})
        download_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_SEGMENT_DOWNLOAD,
            segment_id=10,
            status="success",
        )
        items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_ESSENTIA_TENSORFLOW,
            segment_id=10,
            depends_on_item_id=download_id,
            status="running",
            consumer_group="segment:10",
        )
        cleanup_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_AUDIO_CLEANUP,
            segment_id=None,
            status="pending",
        )
        session.commit()

    svc = PipelineAudioCleanupService(items=items)
    with patch.object(items, "refresh_pipeline_for_job") as refresh_mock:
        svc._run_cleanup_item(cleanup_id)
        refresh_mock.assert_called_once_with(job_id)

    row = next(i for i in items.list_items(job_id) if i["id"] == cleanup_id)
    assert row["status"] == "pending"
    assert row.get("error_code") == "SEGMENT_CONSUMER_PENDING"


def test_ticker_retries_cleanup_after_retry_due(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "cleanup_tick.sqlite"
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

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create(JOB_TYPE_AUDIO_ANALYSIS_PIPELINE)
    past = datetime.now(tz=UTC).replace(tzinfo=None) - timedelta(seconds=120)
    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        job.status = "running"
        job.result_json = json.dumps({"track_count": 1})
        download_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_SEGMENT_DOWNLOAD,
            segment_id=10,
            status="success",
        )
        items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_ESSENTIA_TENSORFLOW,
            segment_id=10,
            depends_on_item_id=download_id,
            status="success",
            consumer_group="segment:10",
        )
        cleanup_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_AUDIO_CLEANUP,
            segment_id=None,
            status="pending",
        )
        session.commit()

    items.mark_failed(
        cleanup_id,
        error_code="SEGMENT_CONSUMER_PENDING",
        error_message="blocked",
        retryable=True,
        retry_delay_seconds=1,
    )

    with patch("app.audio.pipeline.audio_cleanup.AudioCleanupService") as cleanup_cls:
        cleanup_cls.return_value.cleanup_files.return_value = type(
            "R",
            (),
            {"matched_files": 0, "deleted_files": 0, "freed_bytes": 0, "errors": []},
        )()
        AnalysisPipelineTicker(items=items).tick_running_jobs()

    row = next(i for i in items.list_items(job_id) if i["id"] == cleanup_id)
    assert row["status"] == "success"
