from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.database.repositories.track_previews import TrackPreviewsRepository
from app.observability.errors import ApiError
from app.previews.deezer_preview_refresh import ensure_fresh_deezer_preview_url

_MAX_PREVIEW_BYTES = 2 * 1024 * 1024


def fetch_track_preview_audio(
    session: Session,
    track_id: int,
    *,
    http_client: httpx.Client | None = None,
    previews: TrackPreviewsRepository | None = None,
) -> tuple[bytes, str]:
    """Proxy Deezer preview MP3 through the API (same-origin for the UI player)."""
    previews = previews or TrackPreviewsRepository()
    row = previews.get_best_for_track(session, track_id)
    if row is None or not row.preview_url:
        raise ApiError(
            code="PREVIEW_NOT_AVAILABLE",
            message="No Deezer preview available for this track.",
            status_code=404,
        )
    url = ensure_fresh_deezer_preview_url(
        session,
        track_id=track_id,
        preview_url=row.preview_url,
        provider_track_id=row.provider_track_id,
        previews=previews,
        client=None,
    )
    own_client = http_client is None
    client = http_client or httpx.Client(timeout=30.0, follow_redirects=True)
    try:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.content
    except httpx.HTTPError as exc:
        raise ApiError(
            code="PREVIEW_STREAM_FAILED",
            message="Failed to fetch preview audio from provider.",
            status_code=502,
            details={"reason": str(exc)[:500]},
        ) from exc
    finally:
        if own_client:
            client.close()
    if len(data) > _MAX_PREVIEW_BYTES:
        raise ApiError(
            code="PREVIEW_TOO_LARGE",
            message="Preview response exceeds size limit.",
            status_code=502,
        )
    media_type = resp.headers.get("content-type", "audio/mpeg").split(";")[0].strip()
    if not media_type.startswith("audio/"):
        media_type = "audio/mpeg"
    return data, media_type
