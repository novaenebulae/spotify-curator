from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.audio.track_selection import AudioTrackSelectionService
from app.database.models_features import AudioFeature
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.database.repositories.track_advanced_features import (
    AdvancedFeatureUpsertRow,
    TrackAdvancedFeaturesRepository,
)


def _essentia_id(session: Session) -> int:
    src = FeatureSourcesRepository().get_by_name(session, "essentia_lowlevel")
    assert src is not None
    return src.id


def _add_lowlevel(session: Session, *, track_id: int, status: str = "success") -> None:
    session.add(
        AudioFeature(
            track_id=track_id,
            feature_source_id=_essentia_id(session),
            is_active=True,
            status=status,
            bpm=120.0,
            loudness=-8.0,
            key=0,
            mode=1,
            duration_ms=180000,
            created_at=datetime.utcnow(),
            fetched_at=datetime.utcnow(),
        )
    )


def _add_tf_feature(session: Session, *, track_id: int) -> None:
    TrackAdvancedFeaturesRepository().upsert_many(
        session,
        [
            AdvancedFeatureUpsertRow(
                track_id=track_id,
                feature_name="mood_happy_score",
                value_float=0.5,
                confidence=0.9,
                source="essentia_tensorflow",
                status="success",
            ),
        ],
    )


def _resolve(
    session: Session,
    *,
    only_missing: bool = True,
    include_lowlevel: bool = True,
    include_tensorflow: bool = True,
) -> list[int]:
    return AudioTrackSelectionService().resolve_for_advanced_pipeline(
        session,
        track_ids=[1],
        filter_dict=None,
        only_missing=only_missing,
        retry_failed=False,
        force_refresh=False,
        limit=10,
        include_lowlevel=include_lowlevel,
        include_tensorflow=include_tensorflow,
        model_profile="phase6-recommended",
    )


def test_only_missing_includes_when_lowlevel_ok_tf_missing(audio_db) -> None:
    with Session(audio_db) as session:
        _add_lowlevel(session, track_id=1)
        session.commit()
        assert _resolve(session) == [1]


def test_only_missing_includes_when_tf_ok_lowlevel_missing(audio_db) -> None:
    with Session(audio_db) as session:
        _add_tf_feature(session, track_id=1)
        session.commit()
        assert _resolve(session) == [1]


def test_only_missing_excludes_when_both_complete(audio_db) -> None:
    with Session(audio_db) as session:
        _add_lowlevel(session, track_id=1)
        _add_tf_feature(session, track_id=1)
        session.commit()
        assert _resolve(session) == []


def test_only_missing_includes_when_both_missing(audio_db) -> None:
    with Session(audio_db) as session:
        assert _resolve(session) == [1]


def test_only_missing_lowlevel_only_excludes_when_lowlevel_complete(audio_db) -> None:
    with Session(audio_db) as session:
        _add_lowlevel(session, track_id=1)
        session.commit()
        assert _resolve(session, include_tensorflow=False) == []


def test_advanced_api_only_missing_creates_job_when_tf_missing(audio_db, monkeypatch, tmp_path) -> None:
    from fastapi.testclient import TestClient

    from app.database.engine import reset_engine
    from app.main import create_app

    monkeypatch.setenv("DATABASE_URL", str(audio_db.url).replace("sqlite:///", "sqlite:///"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    reset_engine()
    client = TestClient(create_app())

    with Session(audio_db) as session:
        _add_lowlevel(session, track_id=1)
        session.commit()

    res = client.post(
        "/api/v1/audio/analysis/advanced",
        json={
            "track_ids": [1],
            "only_missing": True,
            "include_tensorflow": True,
            "include_lowlevel": True,
        },
    )
    assert res.status_code == 200
    assert res.json()["job_id"]
