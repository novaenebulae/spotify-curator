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
