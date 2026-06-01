from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeezerTrackResult:
    id: str
    title: str
    artist_name: str
    album_title: str | None
    preview_url: str | None
    duration_seconds: float | None
    link: str | None
    isrc: str | None = None


@dataclass(frozen=True)
class PreviewCandidate:
    provider: str
    provider_track_id: str | None
    provider_url: str | None
    preview_url: str | None
    title: str | None
    artist: str | None
    album: str | None
    isrc: str | None
    provider_duration_seconds: float | None
    expected_duration_seconds: float | None
    duration_delta_seconds: float | None
    match_score: float
    match_confidence: float
    is_available: bool
    last_error: str | None = None
