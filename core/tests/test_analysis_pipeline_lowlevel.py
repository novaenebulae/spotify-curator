from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.essentia_parser import parse_essentia_json_file, parsed_segment_to_storage_dict
from app.audio.pipeline.constants import (
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
    STAGE_FEATURE_AGGREGATION,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_audio import TrackSegment
from app.database.models_features import AudioFeature
from app.database.models_job_items import JobItem
from app.database.models_library import Track
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.jobs.items.constants import (
    ITEM_TYPE_ESSENTIA_LOWLEVEL_TRACK,
    JOB_TYPE_ESSENTIA_LOWLEVEL,
    WORKER_TYPE_ESSENTIA_LOWLEVEL,
)
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService
from app.main import create_app
from app.workers.essentia_lowlevel_worker import EssentiaLowlevelWorker
from tests.fixtures.library_seed import seed_library


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


def _planned_a() -> dict:
    return {
        "segment_type": "A",
        "start_seconds": 10.0,
        "end_seconds": 25.0,
        "duration_seconds": 15.0,
        "strategy": "abc_default",
        "source": "youtube",
    }


def _patch_cache_dir(monkeypatch, tmp_path) -> Path:
    cache_root = tmp_path / "cache"
    from app.settings import config

    monkeypatch.setattr(config.settings, "cache_dir", str(cache_root))
    return cache_root


def _segment_with_file(
    session: Session,
    *,
    track_id: int,
    segment_id: int,
    cache_root: Path,
    features_json: str | None = None,
) -> None:
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    rel = f"audio_segments/{track_id}/seg_{segment_id}.wav"
    row = TrackSegment(
        id=segment_id,
        track_id=track_id,
        start_seconds=10.0,
        end_seconds=25.0,
        duration_seconds=15.0,
        segment_type="A",
        source="test",
        temporary_path=rel,
        features_json=features_json,
        created_at=now,
    )
    session.merge(row)
    session.flush()
    wav_path = cache_root / "audio_segments" / str(track_id) / f"seg_{segment_id}.wav"
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(b"\x00\x00\x00\x00")


def test_reserve_pipeline_lowlevel_stage(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "reserve_ll.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=False,
    )

    items = JobItemService()
    for download in [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD]:
        items.mark_success(download["id"])

    reserved = items.reserve_next(worker_id="ll-test", worker_type=WORKER_TYPE_ESSENTIA_LOWLEVEL)
    assert reserved is not None
    assert reserved.job_id == job_id
    with Session(engine) as session:
        row = session.get(JobItem, reserved.id)
        assert row is not None
        assert row.stage_name == STAGE_ESSENTIA_LOWLEVEL


def test_legacy_still_reserves_track_item(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "legacy_ll.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("ANALYSIS_PIPELINE_MODE", "legacy")
    reset_engine()
    init_db()

    from app.settings.config import Settings

    monkeypatch.setattr(
        "app.jobs.items.service.settings",
        Settings(analysis_pipeline_mode="legacy"),
    )

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create(JOB_TYPE_ESSENTIA_LOWLEVEL)
    with Session(engine) as session:
        items.create_items_for_job(
            session,
            job_id=job_id,
            item_type=ITEM_TYPE_ESSENTIA_LOWLEVEL_TRACK,
            track_ids=[1],
        )
        session.commit()

    reserved = items.reserve_next(worker_id="ll-test", worker_type=WORKER_TYPE_ESSENTIA_LOWLEVEL)
    assert reserved is not None
    assert reserved.item_type == ITEM_TYPE_ESSENTIA_LOWLEVEL_TRACK


def test_pipeline_lowlevel_worker_with_fixture(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_ll_worker.sqlite"
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_sample.json"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("ESSENTIA_USE_FIXTURE_JSON", str(fixture))
    cache_root = _patch_cache_dir(monkeypatch, tmp_path)
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        _segment_with_file(session, track_id=1, segment_id=10, cache_root=cache_root)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=False,
    )

    items = JobItemService()
    for download in [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD]:
        items.mark_success(download["id"])

    reserved = items.reserve_next(worker_id="ll-test", worker_type=WORKER_TYPE_ESSENTIA_LOWLEVEL)
    assert reserved is not None

    worker = EssentiaLowlevelWorker()
    worker.process_item(reserved)

    refreshed = items.list_items(job_id, limit=50)
    ll = next(i for i in refreshed if i["id"] == reserved.id)
    assert ll["status"] == "success"
    agg = next(i for i in refreshed if i["stage_name"] == STAGE_FEATURE_AGGREGATION)
    assert agg["status"] == "success"

    with Session(engine) as session:
        src = FeatureSourcesRepository().get_by_name(session, "essentia_lowlevel")
        assert src is not None
        active = session.scalars(
            select(AudioFeature).where(
                AudioFeature.track_id == 1,
                AudioFeature.feature_source_id == src.id,
                AudioFeature.is_active.is_(True),
            )
        ).first()
        assert active is not None
        assert active.bpm is not None


def test_pipeline_lowlevel_idempotent(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_ll_idem.sqlite"
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_sample.json"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("ESSENTIA_USE_FIXTURE_JSON", str(fixture))
    cache_root = _patch_cache_dir(monkeypatch, tmp_path)
    reset_engine()
    init_db()

    parsed = parse_essentia_json_file(str(fixture))
    storage = json.dumps(parsed_segment_to_storage_dict(parsed))
    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        _segment_with_file(
            session,
            track_id=1,
            segment_id=10,
            cache_root=cache_root,
            features_json=storage,
        )
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=False,
    )

    items = JobItemService()
    ll = next(i for i in items.list_items(job_id) if i["stage_name"] == STAGE_ESSENTIA_LOWLEVEL)
    for download in [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD]:
        items.mark_success(download["id"])

    reserved = items.reserve_next(worker_id="ll-test", worker_type=WORKER_TYPE_ESSENTIA_LOWLEVEL)
    worker = EssentiaLowlevelWorker()
    worker.process_item(reserved)

    reserved2 = items.reserve_next(worker_id="ll-test-2", worker_type=WORKER_TYPE_ESSENTIA_LOWLEVEL)
    assert reserved2 is None


def test_feature_aggregation_after_all_lowlevel(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_agg_run.sqlite"
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_sample.json"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    cache_root = _patch_cache_dir(monkeypatch, tmp_path)
    reset_engine()
    init_db()

    parsed = parse_essentia_json_file(str(fixture))
    storage = json.dumps(parsed_segment_to_storage_dict(parsed))
    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        _segment_with_file(
            session, track_id=1, segment_id=10, cache_root=cache_root, features_json=storage
        )
        _segment_with_file(
            session, track_id=1, segment_id=11, cache_root=cache_root, features_json=storage
        )
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10, 11])],
        include_lowlevel=True,
        include_tensorflow=False,
    )

    items = JobItemService()
    for ll in [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_ESSENTIA_LOWLEVEL]:
        with Session(engine) as session:
            assert ll["segment_id"] is not None
            self_seg = session.get(TrackSegment, ll["segment_id"])
            if self_seg:
                self_seg.features_json = storage
            session.commit()
        items.mark_success(ll["id"])

    agg_item = next(
        i for i in items.list_items(job_id) if i["stage_name"] == STAGE_FEATURE_AGGREGATION
    )
    assert agg_item["status"] == "success"


def test_cleanup_blocked_when_tensorflow_stage_pending(tmp_path, monkeypatch) -> None:
    from app.audio.pipeline.consumers import segment_cleanup_allowed

    db_path = tmp_path / "cleanup_tf_block.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.add(
            TrackSegment(
                track_id=1,
                start_seconds=0,
                end_seconds=15,
                duration_seconds=15,
                segment_type="A",
                source="test",
                temporary_path="cache/audio_segments/1/fake.wav",
                created_at=datetime.now(tz=UTC).replace(tzinfo=None),
            )
        )
        session.flush()
        segment_id = 1
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[segment_id])],
        include_lowlevel=True,
        include_tensorflow=True,
    )

    items = JobItemService()
    ll = next(i for i in items.list_items(job_id) if i["stage_name"] == STAGE_ESSENTIA_LOWLEVEL)
    items.mark_success(ll["id"])

    with Session(engine) as session:
        assert not segment_cleanup_allowed(session, segment_id=segment_id)

    tf_items = [
        i
        for i in items.list_items(job_id)
        if i["stage_name"] in (STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,)
    ]
    assert tf_items
    assert any(i["status"] in ("blocked", "pending") for i in tf_items)


def test_pipeline_end_to_end_features_api(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pipeline_features_api.sqlite"
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_sample.json"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("ESSENTIA_USE_FIXTURE_JSON", str(fixture))
    cache_root = _patch_cache_dir(monkeypatch, tmp_path)
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
        _segment_with_file(session, track_id=1, segment_id=10, cache_root=cache_root)
        session.commit()

    orch = AnalysisPipelineOrchestrator()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=False,
    )

    items = JobItemService()
    for download in [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD]:
        items.mark_success(download["id"])

    reserved = items.reserve_next(worker_id="ll-test", worker_type=WORKER_TYPE_ESSENTIA_LOWLEVEL)
    EssentiaLowlevelWorker().process_item(reserved)

    client = TestClient(create_app())
    res = client.get("/api/v1/features/tracks/1")
    assert res.status_code == 200
    data = res.json()
    ess = next(s for s in data["sources"] if s["source_name"] == "essentia_lowlevel")
    assert ess["status"] == "success"
    assert ess["fields"].get("bpm") is not None
