from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import reset_engine
from app.database.models_advanced_features import TrackAdvancedFeature
from app.database.models_track_embeddings import TrackEmbedding
from app.database.repositories.track_advanced_features import AdvancedFeatureUpsertRow, TrackAdvancedFeaturesRepository
from app.database.repositories.track_embeddings import TrackEmbeddingUpsertRow, TrackEmbeddingsRepository
from app.main import create_app


@pytest.fixture
def client(audio_db, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", str(audio_db.url).replace("sqlite:///", "sqlite:///"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    reset_engine()
    return TestClient(create_app())


def test_advanced_coverage_api(client, audio_db) -> None:
    session = Session(audio_db)
    TrackAdvancedFeaturesRepository().upsert_many(
        session,
        [
            AdvancedFeatureUpsertRow(
                track_id=1,
                feature_name="mood_happy_score",
                value_float=0.8,
                confidence=0.9,
                source="essentia_tensorflow",
                model_name="mood_happy",
                pipeline_version="tf_v1",
                status="success",
            ),
        ],
    )
    TrackEmbeddingsRepository().upsert(
        session,
        TrackEmbeddingUpsertRow(
            track_id=1,
            source="essentia_tensorflow",
            model_name="discogs_effnet",
            dimension=4,
            vector_json="[0.1,0.2,0.3,0.4]",
            pipeline_version="tf_v1",
            status="success",
        ),
    )
    session.commit()
    session.close()

    res = client.get("/api/v1/features/advanced/coverage")
    assert res.status_code == 200
    body = res.json()
    assert body["summary"]["track_count"] == 1
    assert body["summary"]["with_any_advanced_features"] >= 1
    assert body["embeddings"]["tracks_with_embedding"] >= 1
    happy = next(f for f in body["features"] if f["feature_name"] == "mood_happy_score")
    assert happy["success_count"] >= 1
    raw = res.text
    assert '"vector"' not in raw or "[0.1" not in raw
