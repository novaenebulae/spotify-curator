from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_jobs import Job
from app.features.enrichment import ReccoBeatsEnrichmentService
from app.jobs.service import JobService


def test_reconcile_orphaned_running_job(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "orphan.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    engine = get_engine()
    with Session(engine) as session:
        session.add(
            Job(
                id="stuck_job",
                job_type="reccobeats_enrichment",
                status="running",
                progress_current=3,
                progress_total=10,
                current_step="enriching_tracks",
                attempt_count=1,
                max_attempts=3,
                result_json="{}",
                last_error="",
                created_at=now,
                started_at=now,
                finished_at=None,
            )
        )
        session.commit()

    reconciled = JobService().reconcile_orphaned_jobs(job_type="reccobeats_enrichment")
    assert reconciled == ["stuck_job"]

    with Session(engine) as session:
        row = session.get(Job, "stuck_job")
        assert row is not None
        assert row.status == "failed"
        assert row.finished_at is not None
        assert "interrupted" in row.last_error.lower()


def test_assert_no_running_job_after_orphan_reconcile(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "orphan2.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    engine = get_engine()
    with Session(engine) as session:
        session.add(
            Job(
                id="stuck2",
                job_type="reccobeats_enrichment",
                status="running",
                progress_current=0,
                progress_total=1,
                current_step="enriching_tracks",
                attempt_count=1,
                max_attempts=3,
                result_json="{}",
                last_error="",
                created_at=now,
                started_at=now,
            )
        )
        session.commit()

    svc = ReccoBeatsEnrichmentService()
    svc.assert_no_running_job()
