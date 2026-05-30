from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.library.schemas import TrackListResponse, TrackSearchFilters
from app.library.search import TrackSearchService

router = APIRouter(prefix="/tracks", tags=["tracks"])
_service = TrackSearchService()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@router.get("", response_model=TrackListResponse)
def list_tracks(
    q: Annotated[str | None, Query()] = None,
    title: Annotated[str | None, Query()] = None,
    artist: Annotated[str | None, Query()] = None,
    album: Annotated[str | None, Query()] = None,
    isrc: Annotated[str | None, Query()] = None,
    liked: Annotated[bool | None, Query()] = None,
    playlist_id: Annotated[int | None, Query()] = None,
    spotify_playlist_id: Annotated[str | None, Query()] = None,
    in_any_playlist: Annotated[bool | None, Query()] = None,
    missing_from_playlists: Annotated[bool | None, Query()] = None,
    availability_status: Annotated[str | None, Query()] = None,
    market_status: Annotated[str | None, Query()] = None,
    snapshot_status: Annotated[str | None, Query()] = None,
    duplicate_status: Annotated[str | None, Query()] = None,
    min_duration_ms: Annotated[int | None, Query()] = None,
    max_duration_ms: Annotated[int | None, Query()] = None,
    added_after: Annotated[str | None, Query()] = None,
    added_before: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    sort: Annotated[str, Query()] = "liked_added_at",
    order: Annotated[str, Query()] = "desc",
) -> TrackListResponse:
    filters = TrackSearchFilters(
        q=q,
        title=title,
        artist=artist,
        album=album,
        isrc=isrc,
        liked=liked,
        playlist_id=playlist_id,
        spotify_playlist_id=spotify_playlist_id,
        in_any_playlist=in_any_playlist,
        missing_from_playlists=missing_from_playlists,
        availability_status=availability_status,
        market_status=market_status,
        snapshot_status=snapshot_status,
        duplicate_status=duplicate_status,
        min_duration_ms=min_duration_ms,
        max_duration_ms=max_duration_ms,
        added_after=_parse_dt(added_after),
        added_before=_parse_dt(added_before),
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )
    return _service.search(filters)
