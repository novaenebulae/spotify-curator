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


def test_reserve_next_distributes_across_workers(tmp_path, monkeypatch) -> None:
    """Each replica must reserve at most one pending item per call (fair horizontal scale)."""
    db_path = tmp_path / "tf_parallel.sqlite"
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

    w1 = items.reserve_next(worker_id="tf-replica-1", worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW)
    w2 = items.reserve_next(worker_id="tf-replica-2", worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW)
    w3 = items.reserve_next(worker_id="tf-replica-3", worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW)

    assert w1 is not None
    assert w2 is not None
    assert w3 is not None
    assert len({w1.id, w2.id, w3.id}) == 3
