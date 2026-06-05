from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_AUDIO_CLEANUP,
    STAGE_FEATURE_AGGREGATION,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.ticker import AnalysisPipelineTicker
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_jobs import Job
from app.database.models_library import Track
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService


def test_ticker_runs_aggregation_for_blocked_job(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "ticker.sqlite"
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
            stage_name=STAGE_FEATURE_AGGREGATION,
            segment_id=None,
            depends_on_item_id=download_id,
            input_payload={"prerequisite_item_ids": [download_id]},
            status="blocked",
        )
        items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_AUDIO_CLEANUP,
            segment_id=None,
            status="blocked",
        )
        session.commit()

    result = AnalysisPipelineTicker(items=items).tick_running_jobs()
    assert result.jobs_ticked >= 1

    rows = items.list_items(job_id)
    agg = next(i for i in rows if i["stage_name"] == STAGE_FEATURE_AGGREGATION)
    assert agg["status"] in ("pending", "skipped", "success")
