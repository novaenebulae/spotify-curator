from datetime import datetime

from sqlalchemy.orm import Session

from app.database.models_library import Track
from app.database.repositories.track_previews import TrackPreviewsRepository


def test_upsert_unique_provider(audio_db) -> None:
    from sqlalchemy.orm import Session

    session = Session(audio_db)
    track = Track(
        name="T",
        normalized_title="t",
        duration_ms=180000,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(track)
    session.flush()
    repo = TrackPreviewsRepository()
    repo.upsert(
        session,
        track_id=track.id,
        provider="deezer",
        fields={"preview_url": "https://a.mp3", "is_available": True},
    )
    repo.upsert(
        session,
        track_id=track.id,
        provider="deezer",
        fields={"preview_url": "https://b.mp3", "is_available": True},
    )
    session.commit()
    row = repo.get_for_track_provider(session, track_id=track.id, provider="deezer")
    assert row is not None
    assert row.preview_url == "https://b.mp3"
