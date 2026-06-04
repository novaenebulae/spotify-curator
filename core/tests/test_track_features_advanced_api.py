from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import reset_engine
from app.database.repositories.track_advanced_features import AdvancedFeatureUpsertRow, TrackAdvancedFeaturesRepository
from app.database.repositories.track_embeddings import TrackEmbeddingUpsertRow, TrackEmbeddingsRepository
from app.main import create_app


@pytest.fixture
def client(audio_db, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", str(audio_db.url).replace("sqlite:///", "sqlite:///"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    reset_engine()
    return TestClient(create_app())


def test_track_features_includes_advanced_block(client, audio_db) -> None:
    session = Session(audio_db)
    TrackAdvancedFeaturesRepository().upsert_many(
        session,
        [
            AdvancedFeatureUpsertRow(
                track_id=1,
                feature_name="mood_happy_score",
                value_float=0.75,
                confidence=0.88,
                source="essentia_tensorflow",
                model_name="mood_happy",
                pipeline_version="tf_v1",
                status="success",
            ),
            AdvancedFeatureUpsertRow(
                track_id=1,
                feature_name="genre_discogs_519_top_k",
                value_float=None,
                confidence=0.5,
                source="essentia_tensorflow",
                model_name="genre_discogs519",
                pipeline_version="tf_v1",
                value_json=json.dumps([{"label": "Electronic", "score": 0.9}]),
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
            dimension=1280,
            vector_json=json.dumps([0.0] * 1280),
            pipeline_version="tf_v1",
            status="success",
            segments_used=2,
        ),
    )
    session.commit()
    session.close()

    res = client.get("/api/v1/features/tracks/1")
    assert res.status_code == 200
    body = res.json()
    assert "resolved_features" in body
    assert isinstance(body["resolved_features"], list)
    assert body["availability"]["has_essentia_tensorflow"] is True
    tf_sources = [s for s in body["sources"] if s["source_name"] == "essentia_tensorflow"]
    assert len(tf_sources) == 1
    adv = body["advanced"]
    assert adv is not None
    assert adv["status"] == "success"
    names = {f["feature_name"] for f in adv["scalar_features"]}
    assert "mood_happy_score" in names
    assert adv["embedding"]["dimension"] == 1280
    assert adv["embedding"]["vector"] is None
    assert len(adv["genre"]["top_k"]) == 1
    assert adv["genre"].get("status") in ("success", "partial", "missing")

    res_vec = client.get("/api/v1/features/tracks/1?include_embedding_vector=true")
    assert res_vec.status_code == 200
    assert len(res_vec.json()["advanced"]["embedding"]["vector"]) == 1280
