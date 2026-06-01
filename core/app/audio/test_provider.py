from __future__ import annotations

import shutil
from pathlib import Path

from app.audio.cleanup import AudioCleanupService
from app.audio.paths import segment_absolute_path, segment_relative_path
from app.audio.provider import AudioSourceCandidate, CleanupResult, PlannedSegment, TrackContext
from app.audio.segments import plan_segments_for_track


class StubAudioProvider:
    """Offline audio provider for tests (pytest-safe name)."""

    def __init__(self, *, fixture_wav: Path | None = None) -> None:
        self._fixture = fixture_wav

    def resolve(self, track: TrackContext) -> list[AudioSourceCandidate]:
        expected = track.duration_ms / 1000.0
        return [
            AudioSourceCandidate(
                source="test",
                url="https://example.com/test-audio",
                candidate_title=track.title,
                candidate_channel=track.primary_artist,
                candidate_duration=expected,
                expected_duration=expected,
                duration_delta=0.0,
                text_match_score=1.0,
                confidence=1.0,
                selected=True,
                rejected_reason=None,
            )
        ]

    def get_segments(
        self,
        track: TrackContext,
        strategy: str,
        *,
        segment_duration_seconds: float | None = None,
    ) -> list[PlannedSegment]:
        return plan_segments_for_track(
            track,
            strategy,
            segment_duration_seconds=segment_duration_seconds,
        )

    def materialize_segment(
        self,
        track: TrackContext,
        *,
        job_id: str,
        segment: PlannedSegment,
    ) -> tuple[str, str]:
        rel = segment_relative_path(
            track_id=track.track_id,
            job_id=job_id,
            segment_type=segment.segment_type,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
        )
        dest = segment_absolute_path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self._fixture and self._fixture.is_file():
            shutil.copyfile(self._fixture, dest)
        else:
            dest.write_bytes(b"RIFF" + b"\x00" * 40)
        return rel, "test-hash"

    def cleanup(
        self,
        job_id: str | None = None,
        track_id: int | None = None,
    ) -> CleanupResult:
        return AudioCleanupService().cleanup_files(job_id=job_id, track_id=track_id)


TestAudioProvider = StubAudioProvider
