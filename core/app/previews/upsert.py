from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.database.repositories.track_previews import TrackPreviewsRepository
from app.previews.schemas import PreviewCandidate


class PreviewUpsertService:
    def __init__(self, repo: TrackPreviewsRepository | None = None) -> None:
        self._repo = repo or TrackPreviewsRepository()

    def upsert_candidate(self, session: Session, *, track_id: int, candidate: PreviewCandidate) -> None:
        now = datetime.utcnow()
        fields = {
            "provider_track_id": candidate.provider_track_id,
            "provider_url": candidate.provider_url,
            "preview_url": candidate.preview_url,
            "duration_seconds": 30.0 if candidate.preview_url else None,
            "format": "mp3" if candidate.preview_url else None,
            "title": candidate.title,
            "artist": candidate.artist,
            "album": candidate.album,
            "isrc": candidate.isrc,
            "provider_duration_seconds": candidate.provider_duration_seconds,
            "expected_duration_seconds": candidate.expected_duration_seconds,
            "duration_delta_seconds": candidate.duration_delta_seconds,
            "match_score": candidate.match_score,
            "match_confidence": candidate.match_confidence,
            "match_strategy": candidate.match_strategy,
            "is_available": candidate.is_available,
            "last_error": candidate.last_error,
            "resolved_at": now if candidate.is_available else None,
            "last_checked_at": now,
        }
        self._repo.upsert(session, track_id=track_id, provider=candidate.provider, fields=fields)
