from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.essentia_parser import parse_essentia_json_file, parsed_segment_to_storage_dict
from app.audio.pipeline.constants import (
    STAGE_FEATURE_AGGREGATION,
)
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_advanced_features import TrackAdvancedFeature
from app.database.models_audio import TrackSegment
from app.database.models_library import Track
from app.jobs.items.constants import WORKER_TYPE_ESSENTIA_TENSORFLOW
from app.jobs.items.service import JobItemService
from app.workers.essentia_tensorflow_worker import EssentiaTensorflowWorker


def _patch_cache(monkeypatch, tmp_path):
    from app.settings import config

    cache_root = tmp_path / "cache"
    monkeypatch.setattr(config.settings, "cache_dir", str(cache_root))
    return cache_root


def _seed_track(session: Session, track_id: int = 1) -> None:
    now = datetime.now(tz=UTC).replace(tzinfo=None)
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


def test_aggregation_writes_advanced_features_and_energy_proxy(
    tmp_path, monkeypatch, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    db_path = tmp_path / "agg_adv.sqlite"
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_sample.json"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    cache_root = _patch_cache(monkeypatch, tmp_path)
    models_dir = build_tf_models(["discogs_effnet_bs64", "mood_happy_discogs_effnet"])
    mm = make_tf_manager(models_dir)

    reset_engine()
    init_db()

    parsed = parse_essentia_json_file(str(fixture))
    storage = json.dumps(parsed_segment_to_storage_dict(parsed))
    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session)
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
                features_json=storage,
                created_at=datetime.now(tz=UTC).replace(tzinfo=None),
            )
        )
        session.commit()
    wav = cache_root / "audio_segments" / "1" / "seg.wav"
    wav.parent.mkdir(parents=True, exist_ok=True)
    wav.write_bytes(b"\x00")

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=True,
    )
    items = JobItemService()
    for row in items.list_items(job_id):
        if row["stage_name"] in ("segment_download", "essentia_lowlevel"):
            items.mark_success(row["id"])

    worker = EssentiaTensorflowWorker(
        model_manager=mm, backend=fake_tf_backend, status_only=False
    )
    while True:
        reserved = items.reserve_next(worker_id="tf", worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW)
        if reserved is None:
            break
        worker.process_item(reserved)
    items.refresh_pipeline_for_job(job_id)

    agg = next(i for i in items.list_items(job_id) if i["stage_name"] == STAGE_FEATURE_AGGREGATION)
    assert agg["status"] == "success"

    with Session(engine) as session:
        rows = list(
            session.scalars(
                select(TrackAdvancedFeature).where(TrackAdvancedFeature.track_id == 1)
            )
        )
    names = {r.feature_name for r in rows}
    assert "energy_proxy" in names
    assert "mood_happy_score" in names
    energy = next(r for r in rows if r.feature_name == "energy_proxy")
    assert energy.source == "derived"
    assert energy.value_float is not None
