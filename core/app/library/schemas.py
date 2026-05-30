from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TrackArtistOut(BaseModel):
    artist_id: int
    spotify_artist_id: str
    name: str


class TrackAlbumOut(BaseModel):
    album_id: int
    spotify_album_id: str
    name: str
    release_date: str | None = None


class TrackPlaylistOut(BaseModel):
    playlist_id: int
    spotify_playlist_id: str
    name: str


class TrackListItem(BaseModel):
    track_id: int
    spotify_track_id: str
    spotify_uri: str
    title: str
    normalized_title: str
    artists: list[TrackArtistOut]
    artist_names: list[str]
    album: TrackAlbumOut | None = None
    duration_ms: int
    explicit: bool
    popularity: int | None = None
    isrc: str | None = None
    liked: bool
    liked_added_at: datetime | None = None
    is_current_liked: bool
    playlist_count: int
    playlists: list[TrackPlaylistOut]
    availability_status: str
    market_status: str
    duplicate_status: str = "none"
    last_seen_at: datetime | None = None
    external_url: str | None = None
    preview_url: str | None = None


class PaginationOut(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class SortOut(BaseModel):
    field: str
    order: str


class TrackListResponse(BaseModel):
    items: list[TrackListItem]
    pagination: PaginationOut
    sort: SortOut
    filters: dict[str, Any] = Field(default_factory=dict)


class TrackSearchFilters(BaseModel):
    q: str | None = None
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    isrc: str | None = None
    liked: bool | None = None
    playlist_id: int | None = None
    spotify_playlist_id: str | None = None
    in_any_playlist: bool | None = None
    missing_from_playlists: bool | None = None
    availability_status: str | None = None
    market_status: str | None = None
    snapshot_status: str | None = None
    duplicate_status: str | None = None
    min_duration_ms: int | None = None
    max_duration_ms: int | None = None
    added_after: datetime | None = None
    added_before: datetime | None = None
    page: int = 1
    page_size: int = 50
    sort: str = "liked_added_at"
    order: str = "desc"
