from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_jobs import Job
from app.jobs.items.constants import ITEM_TYPE_ESSENTIA_LOWLEVEL_TRACK, JOB_TYPE_ESSENTIA_LOWLEVEL
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService


def test_recompute_job_progress_sets_running_while_pending(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "job_progress.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create(JOB_TYPE_ESSENTIA_LOWLEVEL)
    engine = get_engine()

    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        job.progress_total = 3
        job.progress_current = 0
        job.status = "queued"
        session.commit()

        items.create_items_for_job(
            session,
            job_id=job_id,
            item_type=ITEM_TYPE_ESSENTIA_LOWLEVEL_TRACK,
            track_ids=[1, 2, 3],
            input_payload={},
            max_attempts=1,
        )
        session.commit()

    first = items.list_items(job_id, limit=1)[0]
    items.mark_success(first["id"], result_json={})

    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.status == "running"
        assert job.progress_current == 1
        assert job.progress_total == 3
        assert job.current_step == "processing 1/3"


def test_recompute_job_progress_counts_running_items(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "job_progress_running.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create(JOB_TYPE_ESSENTIA_LOWLEVEL)
    engine = get_engine()

    with Session(engine) as session:
        items.create_items_for_job(
            session,
            job_id=job_id,
            item_type=ITEM_TYPE_ESSENTIA_LOWLEVEL_TRACK,
            track_ids=[1, 2],
            input_payload={},
            max_attempts=1,
        )
        session.commit()

    with Session(engine) as session:
        from app.database.repositories.job_items import JobItemsRepository

        row = JobItemsRepository().list_for_job(session, job_id, limit=1)[0]
        JobItemsRepository().update_fields(
            session,
            row.id,
            status="running",
            locked_by="w-test",
            locked_at=datetime.now(tz=UTC).replace(tzinfo=None),
        )
        session.commit()
        items.recompute_job_progress(session, job_id)
        session.commit()
        job = session.get(Job, job_id)
        assert job is not None
        assert job.progress_current == 0
        assert job.progress_total == 2
        assert job.current_step == "processing 0/2"


def test_recompute_job_progress_aggregates_terminal_result(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "job_result_agg.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    from app.jobs.items.constants import (
        ITEM_TYPE_PREVIEW_RESOLVE_TRACK,
        JOB_TYPE_PREVIEW_RESOLVE,
    )

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create(JOB_TYPE_PREVIEW_RESOLVE)
    engine = get_engine()

    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        job.result_json = '{"track_count": 3}'
        items.create_items_for_job(
            session,
            job_id=job_id,
            item_type=ITEM_TYPE_PREVIEW_RESOLVE_TRACK,
            track_ids=[1, 2, 3],
            input_payload={},
            max_attempts=1,
        )
        session.commit()

    listed = items.list_items(job_id, limit=10)
    items.mark_success(listed[0]["id"], result_json={"is_available": True})
    items.mark_success(listed[1]["id"], result_json={"is_available": False})
    items.mark_skipped(listed[2]["id"], reason="Already resolved")

    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.status == "succeeded"
        import json

        result = json.loads(job.result_json or "{}")
        assert result["succeeded"] == 1
        assert result["not_found"] == 1
        assert result["skipped"] == 1
        assert result["track_count"] == 3


def test_cancel_preview_resolve_aggregates_partial_results(tmp_path, monkeypatch) -> None:
    from app.jobs.items.constants import (
        ITEM_TYPE_PREVIEW_RESOLVE_TRACK,
        JOB_TYPE_PREVIEW_RESOLVE,
    )

    db_path = tmp_path / "job_cancel_preview.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create(JOB_TYPE_PREVIEW_RESOLVE)
    engine = get_engine()

    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        job.result_json = '{"track_count": 2}'
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
    items.cancel_pending_for_job(job_id)

    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.status == "cancelled"
        import json

        result = json.loads(job.result_json or "{}")
        assert result["succeeded"] == 1
        assert result["track_count"] == 2
