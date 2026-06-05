from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.audio.pipeline.constants import STAGE_SEGMENT_DOWNLOAD
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_library import Track
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService


def test_mark_failed_retryable_pipeline_stage_refreshes(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "refresh_fail.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        session.add(
            Track(
                id=1,
                name="t",
                normalized_title="t",
                duration_ms=60_000,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create("audio_analysis_pipeline")
    with Session(engine) as session:
        item_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_SEGMENT_DOWNLOAD,
            segment_id=10,
            status="running",
        )
        session.commit()

    with patch.object(items, "refresh_pipeline_for_job") as refresh_mock:
        items.mark_failed(
            item_id,
            error_code="SEGMENT_CONSUMER_PENDING",
            error_message="retry me",
            retryable=True,
            retry_delay_seconds=60,
        )
        refresh_mock.assert_called_once_with(job_id)

    row = next(i for i in items.list_items(job_id) if i["id"] == item_id)
    assert row["status"] == "pending"
