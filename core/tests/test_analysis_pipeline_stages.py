from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_FEATURE_AGGREGATION,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.database.models_library import Track
from app.jobs.items.constants import ITEM_TYPE_AUDIO_DOWNLOAD_TRACK, JOB_TYPE_AUDIO_DOWNLOAD
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService


def _seed_track(session: Session, track_id: int = 1) -> None:
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    if session.get(Track, track_id) is None:
        session.add(
            Track(
                id=track_id,
                name=f"Track {track_id}",
                normalized_title=f"track {track_id}",
                duration_ms=180_000,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()


def _items_by_stage(job_id: str) -> dict[str, list[dict]]:
    items = JobItemService().list_items(job_id, limit=500)
    grouped: dict[str, list[dict]] = {}
    for row in items:
        stage = row.get("stage_name") or "_legacy"
        grouped.setdefault(stage, []).append(row)
    return grouped


def test_create_pipeline_stages_per_segment(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_stages.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [
            TrackSegmentPlan(track_id=1, segment_ids=[10, 11]),
        ],
        include_lowlevel=True,
        include_tensorflow=True,
    )

    grouped = _items_by_stage(job_id)
    assert len(grouped[STAGE_SEGMENT_DOWNLOAD]) == 2
    assert len(grouped[STAGE_ESSENTIA_LOWLEVEL]) == 2
    assert len(grouped[STAGE_ESSENTIA_TENSORFLOW]) == 2
    assert len(grouped[STAGE_FEATURE_AGGREGATION]) == 1

    ll = grouped[STAGE_ESSENTIA_LOWLEVEL][0]
    assert ll["status"] == "blocked"
    assert ll["depends_on_item_id"] is not None
    assert ll["pipeline_version"] == "audio_pipeline_v1"
    assert ll["consumer_group"] == "segment:10"


def test_blocked_until_download_success(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_blocked.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    items = JobItemService()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=False,
    )

    grouped = _items_by_stage(job_id)
    download = grouped[STAGE_SEGMENT_DOWNLOAD][0]
    lowlevel = grouped[STAGE_ESSENTIA_LOWLEVEL][0]
    assert lowlevel["status"] == "blocked"

    items.mark_success(download["id"])
    refreshed = _items_by_stage(job_id)
    assert refreshed[STAGE_ESSENTIA_LOWLEVEL][0]["status"] == "pending"


def test_tensorflow_blocked_until_download(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_tf.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    items = JobItemService()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=False,
        include_tensorflow=True,
    )

    grouped = _items_by_stage(job_id)
    download = grouped[STAGE_SEGMENT_DOWNLOAD][0]
    tensorflow = grouped[STAGE_ESSENTIA_TENSORFLOW][0]
    assert tensorflow["status"] == "blocked"
    assert tensorflow["depends_on_item_id"] == download["id"]

    items.mark_success(download["id"])
    grouped = _items_by_stage(job_id)
    assert grouped[STAGE_ESSENTIA_TENSORFLOW][0]["status"] == "pending"


def test_feature_aggregation_waits_all_segments(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_agg.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    items = JobItemService()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10, 11])],
        include_lowlevel=True,
        include_tensorflow=False,
    )

    grouped = _items_by_stage(job_id)
    agg = grouped[STAGE_FEATURE_AGGREGATION][0]
    assert agg["status"] == "blocked"

    for download in grouped[STAGE_SEGMENT_DOWNLOAD]:
        items.mark_success(download["id"])

    grouped = _items_by_stage(job_id)
    assert grouped[STAGE_FEATURE_AGGREGATION][0]["status"] == "blocked"

    for ll in grouped[STAGE_ESSENTIA_LOWLEVEL]:
        items.mark_success(ll["id"])

    grouped = _items_by_stage(job_id)
    assert grouped[STAGE_FEATURE_AGGREGATION][0]["status"] == "pending"


def test_retry_failed_stage(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_retry.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    items = JobItemService()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=False,
    )

    download = _items_by_stage(job_id)[STAGE_SEGMENT_DOWNLOAD][0]
    items.mark_success(download["id"])
    ll = _items_by_stage(job_id)[STAGE_ESSENTIA_LOWLEVEL][0]
    items.mark_failed(ll["id"], error_code="TEST", error_message="boom", retryable=False)

    with Session(get_engine()) as session:
        row = session.get(JobItem, ll["id"])
        assert row is not None
        assert row.status == "failed"

    assert orch.retry_stage_item(ll["id"]) is True
    refreshed = _items_by_stage(job_id)[STAGE_ESSENTIA_LOWLEVEL][0]
    assert refreshed["status"] == "pending"


def test_job_progress_includes_stage_counts(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_progress.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    items = JobItemService()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=False,
    )

    download = _items_by_stage(job_id)[STAGE_SEGMENT_DOWNLOAD][0]
    items.mark_success(download["id"])

    with Session(engine) as session:
        job = session.get(Job, job_id)
        assert job is not None
        payload = json.loads(job.result_json or "{}")
        assert "stages" in payload
        assert payload["stages"][STAGE_SEGMENT_DOWNLOAD]["success"] >= 1


def test_legacy_job_items_unchanged(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_legacy.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create(JOB_TYPE_AUDIO_DOWNLOAD)

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        items.create_items_for_job(
            session,
            job_id=job_id,
            item_type=ITEM_TYPE_AUDIO_DOWNLOAD_TRACK,
            track_ids=[1],
        )
        session.commit()

    row = items.list_items(job_id)[0]
    assert row.get("stage_name") is None
    assert row["item_type"] == ITEM_TYPE_AUDIO_DOWNLOAD_TRACK
