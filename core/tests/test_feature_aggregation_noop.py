from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_FEATURE_AGGREGATION,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.feature_aggregation import PipelineFeatureAggregationService
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_jobs import Job
from app.database.models_library import Track
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService


def test_aggregation_noop_marks_skipped_not_pending_forever(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "agg_noop.sqlite"
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
        job.result_json = json.dumps({"track_count": 1})
        download_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_SEGMENT_DOWNLOAD,
            segment_id=10,
            status="success",
        )
        ll_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_ESSENTIA_LOWLEVEL,
            segment_id=10,
            depends_on_item_id=download_id,
            status="failed",
        )
        agg_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_FEATURE_AGGREGATION,
            segment_id=None,
            input_payload={"prerequisite_item_ids": [ll_id]},
            status="pending",
        )
        session.commit()

    assert PipelineFeatureAggregationService(items=items)._run_aggregation_item(agg_id) is True

    row = next(i for i in items.list_items(job_id) if i["id"] == agg_id)
    assert row["status"] == "skipped"
    assert "no_features_to_aggregate" in (row.get("error_message") or "")
