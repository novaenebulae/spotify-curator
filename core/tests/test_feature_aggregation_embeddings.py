from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.essentia_parser import parse_essentia_json_file, parsed_segment_to_storage_dict
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_advanced_features import TrackAdvancedFeature
from app.database.models_audio import TrackSegment
from app.database.models_library import Track
from app.database.models_track_embeddings import TrackEmbedding
from app.jobs.items.constants import WORKER_TYPE_ESSENTIA_TENSORFLOW
from app.jobs.items.service import JobItemService
from app.models_registry import ModelRegistry
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


def test_aggregation_persists_embeddings_and_genre(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "agg_emb.sqlite"
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_sample.json"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    cache_root = _patch_cache(monkeypatch, tmp_path)
    models_dir = tmp_path / "models"
    for rel in (
        "discogs_effnet/discogs-effnet-bs64-1.pb",
        "discogs_maest/genre_discogs519-discogs-maest-30s-pw-519l.pb",
        "tensorflow/mood_happy.pb",
    ):
        p = models_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"m")

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
    wav_path = cache_root / "audio_segments" / "1" / "seg.wav"
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(b"\x00")

    job_id = AnalysisPipelineOrchestrator().create_pipeline_job(
        [TrackSegmentPlan(track_id=1, segment_ids=[10])],
        include_lowlevel=True,
        include_tensorflow=True,
    )
    items = JobItemService()
    for row in items.list_items(job_id):
        if row["stage_name"] in ("segment_download", "essentia_lowlevel"):
            items.mark_success(row["id"])

    registry = ModelRegistry(models_dir=str(models_dir))
    worker = EssentiaTensorflowWorker(registry=registry, status_only=False)
    while True:
        reserved = items.reserve_next(worker_id="tf", worker_type=WORKER_TYPE_ESSENTIA_TENSORFLOW)
        if reserved is None:
            break
        worker.process_item(reserved)

    agg = next(i for i in items.list_items(job_id) if i["stage_name"] == "feature_aggregation")
    assert agg["status"] == "success"
    assert agg["result"].get("embeddings_written", 0) >= 1

    with Session(engine) as session:
        emb = list(
            session.scalars(select(TrackEmbedding).where(TrackEmbedding.track_id == 1))
        )
        adv = list(
            session.scalars(
                select(TrackAdvancedFeature).where(TrackAdvancedFeature.track_id == 1)
            )
        )
    assert len(emb) == 1
    assert emb[0].dimension == 1280
    genre_names = {r.feature_name for r in adv}
    assert "genre_discogs_519_top_label" in genre_names
    assert "mood_happy_score" in genre_names
