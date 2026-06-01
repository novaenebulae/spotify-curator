from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.jobs.items.constants import ITEM_TYPE_AUDIO_DOWNLOAD_TRACK
from app.jobs.items.service import JobItemService


def _seed_job(session: Session) -> str:
    job_id = uuid.uuid4().hex
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    session.add(
        Job(
            id=job_id,
            job_type="audio_download",
            status="queued",
            progress_current=0,
            progress_total=1,
            current_step="",
            attempt_count=1,
            max_attempts=3,
            result_json="{}",
            last_error="",
            created_at=now,
        )
    )
    session.commit()
    return job_id


def test_reserve_and_complete_item(audio_db) -> None:
    items_svc = JobItemService()
    with Session(audio_db) as session:
        job_id = _seed_job(session)
        items_svc.create_items_for_job(
            session,
            job_id=job_id,
            item_type=ITEM_TYPE_AUDIO_DOWNLOAD_TRACK,
            track_ids=[1],
        )
        session.commit()

    reserved = items_svc.reserve_next(worker_id="w1", worker_type="audio_downloader")
    assert reserved is not None
    assert reserved.track_id == 1

    items_svc.mark_success(reserved.id, result_json={"ok": True})

    with Session(audio_db) as session:
        row = session.get(JobItem, reserved.id)
        assert row is not None
        assert row.status == "success"
        job = session.get(Job, job_id)
        assert job is not None
        assert job.status == "succeeded"


def test_stale_lock_released(audio_db) -> None:
    items_svc = JobItemService()
    with Session(audio_db) as session:
        job_id = _seed_job(session)
        item_id = uuid.uuid4().hex
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        stale = now - timedelta(hours=2)
        session.add(
            JobItem(
                id=item_id,
                job_id=job_id,
                item_type=ITEM_TYPE_AUDIO_DOWNLOAD_TRACK,
                track_id=1,
                status="running",
                priority=0,
                attempt_count=1,
                max_attempts=3,
                locked_by="old-worker",
                locked_at=stale,
                input_json="{}",
                result_json="{}",
                created_at=now,
            )
        )
        session.commit()

    count = items_svc.release_stale_locks(worker_type="audio_downloader")
    assert count == 1
    reserved = items_svc.reserve_next(worker_id="w2", worker_type="audio_downloader")
    assert reserved is not None
    assert reserved.id == item_id
