from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ReccoBeatsArtist:
    id: str
    name: str
    href: str | None = None


@dataclass(frozen=True)
class ReccoBeatsTrackMeta:
    id: str
    track_title: str
    artists: list[ReccoBeatsArtist]
    duration_ms: int | None
    isrc: str | None
    href: str | None
    spotify_track_id: str | None = None


@dataclass(frozen=True)
class ReccoBeatsAudioFeatures:
    acousticness: float | None = None
    danceability: float | None = None
    energy: float | None = None
    instrumentalness: float | None = None
    key: int | None = None
    liveness: float | None = None
    loudness: float | None = None
    mode: int | None = None
    speechiness: float | None = None
    tempo: float | None = None
    valence: float | None = None
    time_signature: int | None = None
    duration_ms: int | None = None


@dataclass(frozen=True)
class ReccoBeatsFetchResult:
    track: ReccoBeatsTrackMeta | None
    features: ReccoBeatsAudioFeatures | None
    track_raw: dict[str, Any] = field(default_factory=dict)
    features_raw: dict[str, Any] = field(default_factory=dict)
    track_status_code: int | None = None
    features_status_code: int | None = None


@dataclass(frozen=True)
class ReccoBeatsBatchEntry:
    request_id: str
    features: ReccoBeatsAudioFeatures | None
    track: ReccoBeatsTrackMeta | None
    raw: dict[str, Any] = field(default_factory=dict)
    features_status_code: int | None = None


@dataclass(frozen=True)
class ReccoBeatsBatchResult:
    entries: list[ReccoBeatsBatchEntry]
    raw_payload: dict[str, Any]
    status_code: int
