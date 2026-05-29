from app.database.init_db import init_db
from app.jobs.service import JobService


def test_job_lifecycle(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "jobs.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()

    svc = JobService()
    job_id = svc.create("test")

    svc.start_background(job_id, lambda: {"ok": True})

    # Busy-wait briefly: job should complete fast.
    for _ in range(50):
        job = svc.get(job_id)
        assert job is not None
        if job.status in ("succeeded", "failed"):
            break
    job = svc.get(job_id)
    assert job is not None
    assert job.status == "succeeded"
    assert job.result_json == {"ok": True}

