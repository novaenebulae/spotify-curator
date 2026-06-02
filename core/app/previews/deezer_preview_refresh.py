from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.database.repositories.track_previews import TrackPreviewsRepository
from app.previews.deezer_client import DeezerClient, DeezerClientError
from app.previews.deezer_preview_url import is_deezer_preview_url_expired

_logger = logging.getLogger(__name__)


def refresh_stored_deezer_preview_url(
    session: Session,
    *,
    track_id: int,
    provider_track_id: str,
    previews: TrackPreviewsRepository | None = None,
    client: DeezerClient | None = None,
) -> str | None:
    """Fetch a fresh preview URL from Deezer API and persist it on track_previews."""
    previews = previews or TrackPreviewsRepository()
    client = client or DeezerClient()
    try:
        deezer_track = client.get_track(provider_track_id)
    except DeezerClientError as exc:
        _logger.warning(
            "Deezer preview refresh failed track_id=%s deezer_id=%s: %s",
            track_id,
            provider_track_id,
            exc,
        )
        return None

    fresh_url = deezer_track.preview_url
    if not fresh_url:
        return None

    previews.upsert(
        session,
        track_id=track_id,
        provider="deezer",
        fields={"preview_url": fresh_url, "last_checked_at": None},
    )
    session.flush()
    _logger.info(
        "Refreshed Deezer preview URL track_id=%s deezer_id=%s",
        track_id,
        provider_track_id,
    )
    return fresh_url


def ensure_fresh_deezer_preview_url(
    session: Session,
    *,
    track_id: int,
    preview_url: str,
    provider_track_id: str | None,
    previews: TrackPreviewsRepository | None = None,
    client: DeezerClient | None = None,
) -> str:
    """Return preview_url, refreshing from Deezer when the CDN token is expired."""
    if not provider_track_id or not is_deezer_preview_url_expired(preview_url):
        return preview_url
    fresh = refresh_stored_deezer_preview_url(
        session,
        track_id=track_id,
        provider_track_id=provider_track_id,
        previews=previews,
        client=client,
    )
    return fresh or preview_url
