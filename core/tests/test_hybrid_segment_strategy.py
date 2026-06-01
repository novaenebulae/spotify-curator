import pytest

from app.audio.segments import SegmentValidationError, plan_hybrid_for_track
from app.audio.provider import TrackContext
from app.audio.strategy.hybrid import (
    ANALYSIS_DEEZER_ONLY,
    ANALYSIS_DEEZER_PLUS_YT,
    ANALYSIS_UNAVAILABLE,
    ANALYSIS_YT_THREE,
)


def _track(duration_ms: int = 180000) -> TrackContext:
    return TrackContext(
        track_id=1,
        title="T",
        primary_artist="A",
        album=None,
        duration_ms=duration_ms,
    )


def test_nominal_two_youtube_segments() -> None:
    segs, decision = plan_hybrid_for_track(
        _track(),
        deezer_preview_available=True,
        youtube_available=True,
        youtube_confidence=0.9,
    )
    assert decision == ANALYSIS_DEEZER_PLUS_YT
    assert len(segs) == 2
    assert {s.segment_type for s in segs} == {"YOUTUBE_1_3", "YOUTUBE_2_3"}
    assert all(s.duration_seconds <= 30 for s in segs)


def test_youtube_three_fallback() -> None:
    segs, decision = plan_hybrid_for_track(
        _track(),
        deezer_preview_available=False,
        youtube_available=True,
    )
    assert decision == ANALYSIS_YT_THREE
    assert len(segs) == 3


def test_deezer_only_fallback() -> None:
    segs, decision = plan_hybrid_for_track(
        _track(),
        deezer_preview_available=True,
        youtube_available=False,
        deezer_match_confidence=0.8,
    )
    assert decision == ANALYSIS_DEEZER_ONLY
    assert len(segs) == 1
    assert segs[0].segment_type == "DEEZER_PREVIEW"
    assert segs[0].source == "deezer_preview"


def test_local_analysis_unavailable() -> None:
    segs, decision = plan_hybrid_for_track(
        _track(),
        deezer_preview_available=False,
        youtube_available=False,
    )
    assert decision == ANALYSIS_UNAVAILABLE
    assert segs == []


def test_segment_max_30s() -> None:
    segs, _ = plan_hybrid_for_track(
        _track(duration_ms=20000),
        deezer_preview_available=False,
        youtube_available=True,
        segment_duration_seconds=15,
    )
    for s in segs:
        assert s.duration_seconds <= 30


def test_invalid_duration_raises() -> None:
    with pytest.raises(SegmentValidationError):
        plan_hybrid_for_track(
            TrackContext(1, "t", "a", None, 0),
            deezer_preview_available=False,
            youtube_available=True,
        )
