from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_jobs import Job
from app.jobs.items.constants import (
    ITEM_TYPE_PREVIEW_RESOLVE_TRACK,
    JOB_TYPE_PREVIEW_RESOLVE,
    WORKER_TYPE_PREVIEW_RESOLVER,
)
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService
from app.main import create_app


def test_cancel_preview_resolve_cancels_items_and_aggregates(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cancel_api.sqlite'}")
    reset_engine()
    init_db()
    engine = get_engine()

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create(JOB_TYPE_PREVIEW_RESOLVE)
    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        job.progress_total = 2
        job.result_json = json.dumps({"track_count": 2})
        items.create_items_for_job(
            session,
            job_id=job_id,
            item_type=ITEM_TYPE_PREVIEW_RESOLVE_TRACK,
            track_ids=[1, 2],
            input_payload={},
            max_attempts=1,
        )
        session.commit()

    listed = items.list_items(job_id, limit=10)
    items.mark_success(listed[0]["id"], result_json={"is_available": True})

    client = TestClient(create_app())
    res = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert res.status_code == 200

    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.status == "cancelled"
        assert "no active worker" not in (job.last_error or "").lower()
        result = json.loads(job.result_json or "{}")
        assert result.get("succeeded") == 1
        assert result.get("track_count") == 2


def test_reserve_next_skips_cancelled_parent_job(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'reserve_skip.sqlite'}")
    reset_engine()
    init_db()
    engine = get_engine()
    jobs = JobService()
    items = JobItemService()

    old_id = jobs.create(JOB_TYPE_PREVIEW_RESOLVE)
    new_id = jobs.create(JOB_TYPE_PREVIEW_RESOLVE)
    with Session(engine) as session:
        for jid, tid in ((old_id, 1), (new_id, 2)):
            job = session.get(Job, jid)
            assert job is not None
            job.status = "queued"
            items.create_items_for_job(
                session,
                job_id=jid,
                item_type=ITEM_TYPE_PREVIEW_RESOLVE_TRACK,
                track_ids=[tid],
                input_payload={},
                max_attempts=1,
            )
        old = session.get(Job, old_id)
        assert old is not None
        old.status = "cancelled"
        session.commit()

    reserved = items.reserve_next(
        worker_id="w-test", worker_type=WORKER_TYPE_PREVIEW_RESOLVER
    )
    assert reserved is not None
    assert reserved.job_id == new_id
