from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.repositories.track_previews import TrackPreviewsRepository


class HybridAvailabilityService:
    def __init__(self, previews_repo: TrackPreviewsRepository | None = None) -> None:
        self._previews = previews_repo or TrackPreviewsRepository()

    def deezer_for_analysis(self, session: Session, track_id: int) -> tuple[bool, float]:
        """Use Deezer when the preview resolver marked the row available."""
        row = self._previews.get_for_track_provider(session, track_id=track_id, provider="deezer")
        if row is None or not row.is_available or not row.preview_url:
            return False, 0.0
        return True, float(row.match_confidence or 0.0)

    def deezer_for_ui(self, session: Session, track_id: int) -> bool:
        row = self._previews.get_for_track_provider(session, track_id=track_id, provider="deezer")
        return row is not None and bool(row.is_available) and bool(row.preview_url)
