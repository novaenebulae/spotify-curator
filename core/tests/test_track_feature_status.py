from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.database.repositories.track_advanced_features import (
    AdvancedFeatureUpsertRow,
    TrackAdvancedFeaturesRepository,
)
from app.database.repositories.track_previews import TrackPreviewsRepository
from app.library.track_feature_status import batch_feature_status_for_tracks


def test_batch_feature_status(audio_db) -> None:
    from app.database.models_features import AudioFeature

    sources = FeatureSourcesRepository()
    previews = TrackPreviewsRepository()
    session = Session(audio_db)

    rb = sources.get_by_name(session, "reccobeats")
    ess = sources.get_by_name(session, "essentia_lowlevel")
    assert rb is not None
    assert ess is not None

    session.add(
        AudioFeature(
            track_id=1,
            feature_source_id=rb.id,
            is_active=True,
            status="success",
            created_at=datetime.utcnow(),
            fetched_at=datetime.utcnow(),
        )
    )
    session.add(
        AudioFeature(
            track_id=1,
            feature_source_id=ess.id,
            is_active=True,
            status="partial",
            created_at=datetime.utcnow(),
            fetched_at=datetime.utcnow(),
        )
    )
    previews.upsert(
        session,
        track_id=1,
        provider="deezer",
        fields={
            "preview_url": "https://example.com/p.mp3",
            "is_available": True,
            "match_confidence": 0.9,
        },
    )
    TrackAdvancedFeaturesRepository().upsert_many(
        session,
        [
            AdvancedFeatureUpsertRow(
                track_id=1,
                feature_name="mood_happy_score",
                value_float=0.5,
                confidence=0.9,
                source="essentia_tensorflow",
                status="success",
            ),
        ],
    )
    session.commit()

    status = batch_feature_status_for_tracks(session, [1])
    assert status[1]["reccobeats_status"] == "success"
    assert status[1]["essentia_status"] == "partial"
    assert status[1]["local_analysis_status"] == "success"
    assert status[1]["preview_available"] is True
