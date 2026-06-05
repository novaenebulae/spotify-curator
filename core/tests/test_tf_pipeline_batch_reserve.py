from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.pipeline.constants import STAGE_ESSENTIA_TENSORFLOW, STAGE_SEGMENT_DOWNLOAD
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_library import Track
from app.jobs.items.constants import WORKER_TYPE_ESSENTIA_TENSORFLOW
from app.jobs.items.service import JobItemService


def test_reserve_pipeline_stage_batch_limits(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "tf_batch.sqlite"
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

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10, 11, 12])],
        include_lowlevel=False,
        include_tensorflow=True,
    )
    items = JobItemService()
    for download in [
        i for i in items.list_items(job_id) if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD
    ]:
        items.mark_success(download["id"])

    batch = items.reserve_pipeline_stage_batch(
        worker_id="tf-batch",
        worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW,
        stage_names=(STAGE_ESSENTIA_TENSORFLOW,),
        limit=2,
    )
    assert len(batch) == 2
    assert all(r.stage_name == STAGE_ESSENTIA_TENSORFLOW for r in batch)
