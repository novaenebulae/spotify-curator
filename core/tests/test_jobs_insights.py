from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_jobs import Job
from app.main import create_app


def test_latest_jobs_by_type(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "jobs_insights.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    now = datetime.utcnow()
    with Session(engine) as session:
        session.add(
            Job(
                id="job-audio-1",
                job_type="audio_download",
                status="succeeded",
                progress_current=10,
                progress_total=10,
                current_step="done",
                result_json='{"track_count": 10, "segments_created": 8}',
                last_error="",
                created_at=now,
                finished_at=now,
            )
        )
        session.add(
            Job(
                id="job-old",
                job_type="audio_download",
                status="failed",
                progress_current=0,
                progress_total=5,
                current_step="failed",
                result_json="{}",
                last_error="old",
                created_at=now,
                finished_at=now - timedelta(days=1),
            )
        )
        session.commit()

    client = TestClient(create_app())
    res = client.get("/api/v1/jobs/insights/latest")
    assert res.status_code == 200
    jobs = res.json()["jobs"]
    assert jobs["audio_download"] is not None
    assert jobs["audio_download"]["id"] == "job-audio-1"
    assert jobs["audio_download"]["result_json"]["track_count"] == 10
    assert jobs["reccobeats_enrichment"] is None
