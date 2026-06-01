from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class TrackContext:
    track_id: int
    title: str
    primary_artist: str
    album: str | None
    duration_ms: int
    isrc: str | None = None


@dataclass(frozen=True)
class PlannedSegment:
    segment_type: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    strategy: str
    source: str = "youtube"
    source_quality: str = "youtube_representative"
    match_confidence: float = 1.0
    analysis_decision: str = ""


@dataclass(frozen=True)
class AudioSourceCandidate:
    source: str
    url: str
    candidate_title: str
    candidate_channel: str
    candidate_duration: float | None
    expected_duration: float | None
    duration_delta: float | None
    text_match_score: float
    confidence: float
    selected: bool = False
    rejected_reason: str | None = None


@dataclass
class CleanupResult:
    matched_files: int = 0
    deleted_files: int = 0
    freed_bytes: int = 0
    errors: list[str] = field(default_factory=list)


class AudioProvider(Protocol):
    def resolve(self, track: TrackContext) -> list[AudioSourceCandidate]: ...

    def get_segments(
        self,
        track: TrackContext,
        strategy: str,
        *,
        segment_duration_seconds: float | None = None,
    ) -> list[PlannedSegment]: ...

    def cleanup(
        self,
        job_id: str | None = None,
        track_id: int | None = None,
    ) -> CleanupResult: ...
