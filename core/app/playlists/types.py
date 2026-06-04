from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

FeatureStatus = Literal[
    "available",
    "missing",
    "not_available_yet",
    "invalid",
    "low_confidence",
    "source_failed",
    "not_applicable",
    "model_missing",
]


@dataclass(frozen=True)
class FeatureDescriptor:
    name: str
    label: str
    value_type: str
    range_min: float | None = None
    range_max: float | None = None
    available_sources: tuple[str, ...] = ()
    future_sources: tuple[str, ...] = ()
    phase_available: int = 5
    normalization: str = "identity"
    missing_policy: str = "exclude_if_required"
    is_alias: bool = False
    alias_of: str | None = None


@dataclass
class FeatureValue:
    name: str
    value: Any | None = None
    confidence: float | None = None
    source: str | None = None
    source_version: str | None = None
    status: FeatureStatus = "missing"
    missing_reason: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class TrackFeatureView:
    track_id: int
    spotify_track_id: str | None
    title: str
    artist_names: list[str]
    artist_ids: list[int]
    album_id: int | None
    album_name: str | None
    isrc: str | None
    duration_ms: int | None
    availability_status: str | None
    market_status: str | None
    liked: bool | None
    playlist_ids: list[int]
    duplicate_status: str | None
    preview_available: bool
    features: dict[str, FeatureValue]

    def get(self, name: str) -> FeatureValue | None:
        return self.features.get(name)
