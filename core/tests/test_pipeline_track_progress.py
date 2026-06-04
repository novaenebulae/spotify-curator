from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_AUDIO_CLEANUP,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_jobs import Job
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService


@pytest.fixture
def progress_db(tmp_path, monkeypatch):
    db_path = tmp_path / "track_progress.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()
    return get_engine()


def test_download_ok_stays_pending_until_cleanup(progress_db) -> None:
    """Segment download success does not count as track completed."""
    items = JobItemService()
    jobs = JobService()
    job_id = jobs.create(JOB_TYPE_AUDIO_ANALYSIS_PIPELINE)
    with Session(progress_db) as session:
        job = session.get(Job, job_id)
        assert job is not None
        job.result_json = json.dumps({"track_count": 1})
        session.commit()

    with Session(progress_db) as session:
        items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_SEGMENT_DOWNLOAD,
            segment_id=10,
            consumer_group="g1",
            pipeline_version="v1",
            input_payload={"track_id": 1},
            status="success",
        )
        session.commit()

    prog = items.pipeline_track_progress(job_id)
    assert prog["tracks_total"] == 1
    assert prog["tracks_completed"] == 0
    assert prog["tracks_pending"] == 1
    assert prog["tracks_failed"] == 0


def test_track_completed_after_cleanup_success(progress_db) -> None:
    items = JobItemService()
    jobs = JobService()
    job_id = jobs.create(JOB_TYPE_AUDIO_ANALYSIS_PIPELINE)
    with Session(progress_db) as session:
        job = session.get(Job, job_id)
        assert job is not None
        job.result_json = json.dumps({"track_count": 2})
        session.commit()

    with Session(progress_db) as session:
        for tid in (1, 2):
            items.create_pipeline_stage_item(
                session,
                job_id=job_id,
                track_id=tid,
                stage_name=STAGE_SEGMENT_DOWNLOAD,
                segment_id=tid * 10,
                consumer_group="g1",
                pipeline_version="v1",
                input_payload={"track_id": tid},
                status="success",
            )
            items.create_pipeline_stage_item(
                session,
                job_id=job_id,
                track_id=tid,
                stage_name=STAGE_AUDIO_CLEANUP,
                segment_id=None,
                consumer_group="g1",
                pipeline_version="v1",
                input_payload={"track_id": tid},
                status="success",
            )
        session.commit()

    prog = items.pipeline_track_progress(job_id)
    assert prog["tracks_total"] == 2
    assert prog["tracks_completed"] == 2
    assert prog["tracks_failed"] == 0
    assert prog["tracks_pending"] == 0
