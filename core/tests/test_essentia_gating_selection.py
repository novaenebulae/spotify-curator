from sqlalchemy.orm import Session

from app.audio.track_selection import AudioTrackSelectionService
from app.database.models_features import AudioFeature
from app.database.repositories.feature_sources import FeatureSourcesRepository


def _source_id(session: Session, name: str) -> int:
    src = FeatureSourcesRepository().get_by_name(session, name)
    assert src is not None
    return src.id


def test_gating_includes_when_reccobeats_missing(audio_db) -> None:
    svc = AudioTrackSelectionService()
    with Session(audio_db) as session:
        ids = svc.resolve_for_analysis(
            session,
            track_ids=[1],
            filter_dict=None,
            only_missing=True,
            retry_failed=False,
            force_refresh=False,
            limit=10,
            require_existing_segments=False,
        )
    assert ids == [1]


def test_download_selection_skips_when_essentia_already_success(audio_db) -> None:
    from app.audio.track_selection import AudioTrackSelectionService
    from app.database.models_features import AudioFeature
    from app.database.repositories.feature_sources import FeatureSourcesRepository

    svc = AudioTrackSelectionService()
    with Session(audio_db) as session:
        essentia = FeatureSourcesRepository().get_by_name(session, "essentia_lowlevel")
        assert essentia is not None
        session.add(
            AudioFeature(
                track_id=1,
                feature_source_id=essentia.id,
                is_active=True,
                status="success",
                bpm=120.0,
                loudness=-8.0,
                key=0,
                mode=1,
                duration_ms=180000,
            )
        )
        session.commit()
        ids = svc.resolve_for_download(
            session,
            track_ids=[1],
            filter_dict=None,
            only_missing=True,
            retry_failed=False,
            limit=10,
        )
    assert ids == []


def test_gating_skips_when_reccobeats_complete(audio_db) -> None:
    svc = AudioTrackSelectionService()
    with Session(audio_db) as session:
        rb_id = _source_id(session, "reccobeats")
        session.add(
            AudioFeature(
                track_id=1,
                feature_source_id=rb_id,
                is_active=True,
                status="success",
                bpm=120.0,
                loudness=-8.0,
                key=0,
                mode=1,
                duration_ms=180000,
            )
        )
        session.commit()

        ids = svc.resolve_for_analysis(
            session,
            track_ids=[1],
            filter_dict=None,
            only_missing=True,
            retry_failed=False,
            force_refresh=False,
            limit=10,
            require_existing_segments=False,
        )
    assert ids == []


def test_gating_includes_when_reccobeats_missing_bpm(audio_db) -> None:
    svc = AudioTrackSelectionService()
    with Session(audio_db) as session:
        rb_id = _source_id(session, "reccobeats")
        session.add(
            AudioFeature(
                track_id=1,
                feature_source_id=rb_id,
                is_active=True,
                status="success",
                bpm=None,
                loudness=-8.0,
                key=0,
                mode=1,
                duration_ms=180000,
            )
        )
        session.commit()

        ids = svc.resolve_for_analysis(
            session,
            track_ids=[1],
            filter_dict=None,
            only_missing=True,
            retry_failed=False,
            force_refresh=False,
            limit=10,
            require_existing_segments=False,
        )
    assert ids == [1]

