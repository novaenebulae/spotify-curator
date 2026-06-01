from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_jobs import Job
from app.main import create_app


def test_get_job_maps_succeeded_to_success(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'job.sqlite'}")
    init_db()
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    with Session(get_engine()) as session:
        session.add(
            Job(
                id="done1",
                job_type="reccobeats_enrichment",
                status="succeeded",
                progress_current=10,
                progress_total=10,
                current_step="complete",
                attempt_count=1,
                max_attempts=3,
                result_json='{"succeeded": 10}',
                last_error="",
                created_at=now,
                started_at=now,
                finished_at=now,
            )
        )
        session.commit()

    res = TestClient(create_app()).get("/api/v1/jobs/done1")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["result"]["succeeded"] == 10
