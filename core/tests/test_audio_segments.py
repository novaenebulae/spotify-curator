from __future__ import annotations

import pytest

from app.audio.provider import TrackContext
from app.audio.segments import (
    SegmentValidationError,
    plan_segments_abc_default,
    validate_segment_duration,
)
from app.settings.config import settings


def _ctx(duration_ms: int) -> TrackContext:
    return TrackContext(
        track_id=1,
        title="T",
        primary_artist="A",
        album=None,
        duration_ms=duration_ms,
    )


@pytest.mark.parametrize(
    "duration_s,expected_count",
    [
        (20, 1),
        (45, 3),
        (90, 3),
        (180, 3),
        (600, 3),
    ],
)
def test_abc_default_segment_counts(duration_s: int, expected_count: int) -> None:
    segs = plan_segments_abc_default(float(duration_s), segment_duration_seconds=15)
    assert len(segs) == expected_count
    for s in segs:
        assert s.duration_seconds <= settings.audio_segment_max_seconds
        assert s.duration_seconds > 0
        assert s.end_seconds <= duration_s + 0.001


def test_segment_duration_deterministic() -> None:
    a = plan_segments_abc_default(180.0, segment_duration_seconds=15)
    b = plan_segments_abc_default(180.0, segment_duration_seconds=15)
    assert [(s.segment_type, s.start_seconds, s.end_seconds) for s in a] == [
        (s.segment_type, s.start_seconds, s.end_seconds) for s in b
    ]


def test_rejects_segment_over_30s() -> None:
    with pytest.raises(SegmentValidationError):
        validate_segment_duration(31.0)


def test_plan_clamps_segment_duration_to_max(monkeypatch) -> None:
    monkeypatch.setattr(settings, "audio_segment_max_seconds", 30.0)
    segs = plan_segments_abc_default(300.0, segment_duration_seconds=35)
    assert all(s.duration_seconds <= 30.0 for s in segs)
