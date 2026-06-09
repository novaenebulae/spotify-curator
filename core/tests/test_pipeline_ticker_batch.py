from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_AUDIO_CLEANUP,
    STAGE_FEATURE_AGGREGATION,
)
from app.audio.pipeline.ticker import AnalysisPipelineTicker
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_jobs import Job
from app.database.models_library import Track
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService
from app.settings import config


def test_ticker_limits_aggregation_and_cleanup_batches(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "ticker_batch.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setattr(config.settings, "analysis_pipeline_agg_batch_size", 2)
    monkeypatch.setattr(config.settings, "analysis_pipeline_cleanup_batch_size", 2)
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
        job.result_json = json.dumps({"track_count": 3})
        for track_id in (1, 2, 3):
            items.create_pipeline_stage_item(
                session,
                job_id=job_id,
                track_id=track_id,
                stage_name=STAGE_FEATURE_AGGREGATION,
                segment_id=None,
                status="pending",
            )
            items.create_pipeline_stage_item(
                session,
                job_id=job_id,
                track_id=track_id,
                stage_name=STAGE_AUDIO_CLEANUP,
                segment_id=None,
                status="pending",
            )
        session.commit()

    agg = MagicMock()
    agg.try_run_pending_for_job.return_value = 2
    cleanup = MagicMock()
    cleanup.try_run_pending_for_job.return_value = 2

    ticker = AnalysisPipelineTicker(items=items, aggregation=agg, cleanup=cleanup)
    ticker.tick_running_jobs()

    agg.try_run_pending_for_job.assert_called_once_with(job_id)
    cleanup.try_run_pending_for_job.assert_called_once_with(job_id)
