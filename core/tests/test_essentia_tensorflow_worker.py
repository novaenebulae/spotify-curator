from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
    STAGE_FEATURE_AGGREGATION,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_audio import TrackSegment
from app.database.models_job_items import JobItem
from app.database.models_library import Track
from app.jobs.items.constants import WORKER_TYPE_ESSENTIA_TENSORFLOW
from app.jobs.items.service import JobItemService
from app.workers.essentia_tensorflow_worker import EssentiaTensorflowWorker


def _seed_track(session: Session, track_id: int = 1) -> None:
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    if session.get(Track, track_id) is None:
        session.add(
            Track(
                id=track_id,
                name="t",
                normalized_title="t",
                duration_ms=60_000,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()


def _patch_cache(monkeypatch, tmp_path) -> Path:
    cache_root = tmp_path / "cache"
    from app.settings import config

    monkeypatch.setattr(config.settings, "cache_dir", str(cache_root))
    return cache_root


def test_reserve_unified_tf_stage_first(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "reserve_tf.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        session.commit()

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=False,
        include_tensorflow=True,
    )

    items = JobItemService()
    for download in [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD]:
        items.mark_success(download["id"])

    reserved = items.reserve_next(
        worker_id="tf-test", worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW
    )
    assert reserved is not None
    with Session(engine) as session:
        row = session.get(JobItem, reserved.id)
        assert row is not None
        assert row.stage_name == STAGE_ESSENTIA_TENSORFLOW


def test_worker_status_only_skips_and_unblocks_aggregation(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "tf_status_only.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    cache_root = _patch_cache(monkeypatch, tmp_path)
    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        rel = "audio_segments/1/seg.wav"
        session.add(
            TrackSegment(
                id=10,
                track_id=1,
                start_seconds=0,
                end_seconds=15,
                duration_seconds=15,
                segment_type="A",
                source="test",
                temporary_path=rel,
                created_at=datetime.now(tz=UTC).replace(tzinfo=None),
            )
        )
        session.flush()
        session.commit()
    wav = cache_root / "audio_segments" / "1" / "seg.wav"
    wav.parent.mkdir(parents=True, exist_ok=True)
    wav.write_bytes(b"\x00\x00")

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=True,
    )

    items = JobItemService()
    for download in [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD]:
        items.mark_success(download["id"])
    for ll in [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_ESSENTIA_LOWLEVEL]:
        items.mark_success(ll["id"])

    worker = EssentiaTensorflowWorker(status_only=True)
    while True:
        reserved = items.reserve_next(
            worker_id="tf-worker", worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW
        )
        if reserved is None:
            break
        worker.process_item(reserved)
    items.refresh_pipeline_for_job(job_id)

    refreshed = items.list_items(job_id, limit=50)
    tf = next(i for i in refreshed if i["stage_name"] == STAGE_ESSENTIA_TENSORFLOW)
    assert tf["status"] == "skipped"
    agg = next(i for i in refreshed if i["stage_name"] == STAGE_FEATURE_AGGREGATION)
    assert agg["status"] in ("pending", "success")


def test_worker_real_success_with_fake_backend(
    tmp_path, monkeypatch, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    db_path = tmp_path / "tf_real.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    cache_root = _patch_cache(monkeypatch, tmp_path)
    models_dir = build_tf_models(
        ["discogs_effnet_bs64", "discogs_maest_30s_pw_519l", "genre_discogs519_maest_519l"]
    )
    mm = make_tf_manager(models_dir)

    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        rel = "audio_segments/1/seg.wav"
        session.add(
            TrackSegment(
                id=10,
                track_id=1,
                start_seconds=0,
                end_seconds=15,
                duration_seconds=15,
                segment_type="A",
                source="test",
                temporary_path=rel,
                created_at=datetime.now(tz=UTC).replace(tzinfo=None),
            )
        )
        session.flush()
        session.commit()
    (cache_root / "audio_segments" / "1" / "seg.wav").parent.mkdir(parents=True, exist_ok=True)
    (cache_root / "audio_segments" / "1" / "seg.wav").write_bytes(b"\x00\x01\x02\x03")

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=False,
        include_tensorflow=True,
    )

    items = JobItemService()
    for download in [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD]:
        items.mark_success(download["id"])

    worker = EssentiaTensorflowWorker(
        model_manager=mm, backend=fake_tf_backend, status_only=False
    )
    reserved = items.reserve_next(worker_id="tf", worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW)
    assert reserved is not None
    worker.process_item(reserved)
    items.refresh_pipeline_for_job(job_id)

    row = next(i for i in items.list_items(job_id) if i["id"] == reserved.id)
    assert row["status"] == "success"
    assert row["result"]["inference"] == "real"
    assert row["result"]["pipeline_version"]


def test_worker_unified_emit_all_outputs(
    tmp_path, monkeypatch, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    db_path = tmp_path / "tf_emb_out.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    cache_root = _patch_cache(monkeypatch, tmp_path)
    models_dir = build_tf_models(
        [
            "discogs_effnet_bs64",
            "discogs_maest_30s_pw_519l",
            "genre_discogs519_maest_519l",
            "mood_happy_discogs_effnet",
        ]
    )
    mm = make_tf_manager(models_dir)

    reset_engine()
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        rel = "audio_segments/1/seg.wav"
        session.add(
            TrackSegment(
                id=10,
                track_id=1,
                start_seconds=0,
                end_seconds=15,
                duration_seconds=15,
                segment_type="A",
                source="test",
                temporary_path=rel,
                created_at=datetime.now(tz=UTC).replace(tzinfo=None),
            )
        )
        session.commit()
    wav_path = cache_root / "audio_segments" / "1" / "seg.wav"
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(b"\x00\x07\x08")

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=False,
        include_tensorflow=True,
    )
    items = JobItemService()
    for download in [i for i in items.list_items(job_id) if i["stage_name"] == STAGE_SEGMENT_DOWNLOAD]:
        items.mark_success(download["id"])

    worker = EssentiaTensorflowWorker(
        model_manager=mm, backend=fake_tf_backend, status_only=False
    )
    reserved = items.reserve_next(worker_id="tf", worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW)
    assert reserved is not None
    worker.process_item(reserved)

    tf_row = next(
        i for i in items.list_items(job_id) if i["stage_name"] == STAGE_ESSENTIA_TENSORFLOW
    )
    assert tf_row["status"] == "success"
    assert tf_row["result"]["inference"] == "real"
    assert "embedding_outputs" in tf_row["result"]
    assert "genre_outputs" in tf_row["result"]
    assert "classifier_outputs" in tf_row["result"]
    assert "mood_happy" in tf_row["result"]["classifier_outputs"]


def test_legacy_classifiers_skipped_when_embeddings_has_outputs(
    tmp_path, monkeypatch, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    db_path = tmp_path / "tf_legacy_skip.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    cache_root = _patch_cache(monkeypatch, tmp_path)
    models_dir = build_tf_models(["discogs_effnet_bs64", "mood_happy_discogs_effnet"])
    mm = make_tf_manager(models_dir)

    reset_engine()
    init_db()

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session, 1)
        rel = "audio_segments/1/seg.wav"
        session.add(
            TrackSegment(
                id=10,
                track_id=1,
                start_seconds=0,
                end_seconds=15,
                duration_seconds=15,
                segment_type="A",
                source="test",
                temporary_path=rel,
                created_at=datetime.now(tz=UTC).replace(tzinfo=None),
            )
        )
        session.commit()
    wav_path = cache_root / "audio_segments" / "1" / "seg.wav"
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(b"\x00\x05\x06\x07")

    orch = AnalysisPipelineOrchestrator()
    items = JobItemService()
    job_id = orch.create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=False,
        include_tensorflow=False,
    )
    with Session(engine) as session:
        download_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_SEGMENT_DOWNLOAD,
            segment_id=10,
            status="success",
        )
        emb_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
            segment_id=10,
            depends_on_item_id=download_id,
            status="pending",
        )
        clf_id = items.create_pipeline_stage_item(
            session,
            job_id=job_id,
            track_id=1,
            stage_name=STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
            segment_id=10,
            depends_on_item_id=emb_id,
            status="pending",
        )
        session.commit()

    items.mark_success(
        emb_id,
        result_json={
            "segment_id": 10,
            "classifier_outputs": {"mood_happy": {"probability": 0.9}},
            "embedding_outputs": {},
            "genre_outputs": {},
            "models_missing": [],
            "inference": "real",
        },
    )

    worker = EssentiaTensorflowWorker(
        model_manager=mm, backend=fake_tf_backend, status_only=False
    )
    reserved = items.reserve_next(worker_id="tf", worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW)
    assert reserved is not None
    assert reserved.id == clf_id
    worker.process_item(reserved)

    clf_row = next(
        i for i in items.list_items(job_id) if i["stage_name"] == STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS
    )
    assert clf_row["status"] == "skipped"
