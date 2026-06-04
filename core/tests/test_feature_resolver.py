from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.database.repositories.track_advanced_features import (
    AdvancedFeatureUpsertRow,
    TrackAdvancedFeaturesRepository,
)
from app.playlists.feature_resolver import FeatureResolver
from tests.fixtures.library_seed import seed_library
from tests.test_track_features_api import _seed_reccobeats


def _db(tmp_path, monkeypatch):
    db_path = tmp_path / "resolver.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        ids = seed_library(session)
        track_id = int(ids["sp_t1"])
        _seed_reccobeats(session, track_id)
        session.commit()
    return engine, track_id


def test_resolver_returns_track_feature_view(tmp_path, monkeypatch) -> None:
    engine, track_id = _db(tmp_path, monkeypatch)
    resolver = FeatureResolver()
    with Session(engine) as session:
        views = resolver.load_views(session, [track_id])
    assert track_id in views
    view = views[track_id]
    assert view.title == "Track One"
    energy = view.features.get("energy")
    assert energy is not None
    assert energy.status == "available"
    assert energy.value is not None


def test_resolver_future_feature_not_available_yet(tmp_path, monkeypatch) -> None:
    engine, track_id = _db(tmp_path, monkeypatch)
    resolver = FeatureResolver()
    with Session(engine) as session:
        views = resolver.load_views(session, [track_id])
    mood = views[track_id].features.get("mood_dark_score")
    assert mood is not None
    assert mood.status == "not_available_yet"
    assert mood.missing_reason == "FEATURE_NOT_AVAILABLE_YET"


def test_resolver_keeps_reccobeats_energy_when_present(tmp_path, monkeypatch) -> None:
    engine, track_id = _db(tmp_path, monkeypatch)
    with Session(engine) as session:
        TrackAdvancedFeaturesRepository().upsert_many(
            session,
            [
                AdvancedFeatureUpsertRow(
                    track_id=track_id,
                    feature_name="energy_proxy",
                    value_float=0.99,
                    confidence=0.9,
                    source="derived",
                    pipeline_version="low_v1",
                )
            ],
        )
        session.commit()
    resolver = FeatureResolver()
    with Session(engine) as session:
        energy = resolver.load_views(session, [track_id])[track_id].features["energy"]
    assert energy is not None
    assert energy.source == "reccobeats"
    assert energy.value != 0.99


def test_resolver_falls_back_to_energy_proxy(tmp_path, monkeypatch) -> None:
    engine, track_id = _db(tmp_path, monkeypatch)
    with Session(engine) as session:
        sources = FeatureSourcesRepository()
        rb = sources.get_by_name(session, "reccobeats")
        assert rb is not None
        AudioFeaturesRepository().deactivate_active_for_track_source(
            session, track_id=track_id, feature_source_id=rb.id
        )
        TrackAdvancedFeaturesRepository().upsert_many(
            session,
            [
                AdvancedFeatureUpsertRow(
                    track_id=track_id,
                    feature_name="energy_proxy",
                    value_float=0.42,
                    confidence=0.8,
                    source="derived",
                    pipeline_version="low_v1",
                )
            ],
        )
        session.commit()
    resolver = FeatureResolver()
    with Session(engine) as session:
        energy = resolver.load_views(session, [track_id])[track_id].features["energy"]
    assert energy is not None
    assert energy.status == "available"
    assert energy.value == 0.42
    assert energy.source == "derived"


def test_resolver_mood_from_advanced_and_model_missing(tmp_path, monkeypatch) -> None:
    engine, track_id = _db(tmp_path, monkeypatch)
    with Session(engine) as session:
        repo = TrackAdvancedFeaturesRepository()
        repo.upsert_many(
            session,
            [
                AdvancedFeatureUpsertRow(
                    track_id=track_id,
                    feature_name="mood_happy_score",
                    value_float=0.7,
                    confidence=0.85,
                    source="essentia_tensorflow",
                    model_name="mood_happy",
                    pipeline_version="tf_v1",
                ),
                AdvancedFeatureUpsertRow(
                    track_id=track_id,
                    feature_name="approachability",
                    value_float=None,
                    confidence=None,
                    source="essentia_tensorflow",
                    model_name="approachability",
                    pipeline_version="tf_v1",
                    status="model_missing",
                ),
            ],
        )
        session.commit()
    resolver = FeatureResolver()
    with Session(engine) as session:
        view = resolver.load_views(session, [track_id])[track_id]
    happy = view.features.get("mood_happy_score")
    assert happy is not None
    assert happy.status == "available"
    assert happy.value == 0.7
    approach = view.features.get("approachability")
    assert approach is not None
    assert approach.status == "model_missing"


def test_resolver_exposes_embeddings_and_genre(tmp_path, monkeypatch) -> None:
    import json

    from app.database.repositories.track_embeddings import (
        TrackEmbeddingUpsertRow,
        TrackEmbeddingsRepository,
    )

    engine, track_id = _db(tmp_path, monkeypatch)
    vec = [0.5] * 1280
    with Session(engine) as session:
        TrackEmbeddingsRepository().upsert(
            session,
            TrackEmbeddingUpsertRow(
                track_id=track_id,
                source="essentia_tensorflow",
                model_name="discogs_effnet_embeddings",
                dimension=1280,
                vector_json=json.dumps(vec),
                pipeline_version="tf_v1",
                confidence=0.88,
            ),
        )
        TrackAdvancedFeaturesRepository().upsert_many(
            session,
            [
                AdvancedFeatureUpsertRow(
                    track_id=track_id,
                    feature_name="genre_discogs_519_top_label",
                    value_text="Techno",
                    value_float=None,
                    confidence=0.6,
                    source="essentia_tensorflow",
                    model_name="genre_discogs_519",
                    pipeline_version="tf_v1",
                ),
                AdvancedFeatureUpsertRow(
                    track_id=track_id,
                    feature_name="genre_discogs_519_top_score",
                    value_float=0.6,
                    confidence=0.6,
                    source="essentia_tensorflow",
                    model_name="genre_discogs_519",
                    pipeline_version="tf_v1",
                ),
            ],
        )
        session.commit()

    resolver = FeatureResolver()
    with Session(engine) as session:
        view = resolver.load_views(session, [track_id])[track_id]

    style = view.features.get("style_embedding")
    assert style is not None
    assert style.status == "available"
    assert isinstance(style.value, list)
    assert len(style.value) == 1280

    timbre = view.features.get("timbre_embedding")
    assert timbre is not None
    assert len(timbre.value) == 256

    label = view.features.get("genre_discogs_519_top_label")
    assert label is not None
    assert label.value == "Techno"
