from sqlalchemy.orm import Session

from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_library import Track
from app.jobs.service import JobService
from app.library.job_progress import report_job_progress


def test_report_job_progress_commits_before_job_update(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "progress.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    jobs = JobService()
    job_id = jobs.create("test_progress")
    engine = get_engine()

    with Session(engine) as session:
        session.add(Track(name="hold-lock", duration_ms=1, explicit=False, raw_json="{}"))
        session.flush()

        report_job_progress(
            session,
            jobs,
            job_id,
            force=True,
            progress_current=1,
            progress_total=10,
            current_step="Importing 1/10",
        )

    status = jobs.get(job_id)
    assert status is not None
    assert status.progress_current == 1
    assert status.current_step == "Importing 1/10"
