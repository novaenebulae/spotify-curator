from __future__ import annotations

from app.audio.provider import PlannedSegment, TrackContext
from app.observability.errors import ApiError
from app.settings.config import settings

ABC_ZONES: tuple[tuple[str, float, float], ...] = (
    ("A", 0.10, 0.25),
    ("B", 0.45, 0.60),
    ("C", 0.70, 0.85),
)


class SegmentValidationError(ValueError):
    pass


def validate_segment_duration(duration_seconds: float) -> None:
    if duration_seconds <= 0:
        raise SegmentValidationError("Segment duration must be positive")
    if duration_seconds > settings.audio_segment_max_seconds:
        raise SegmentValidationError(
            f"Segment duration {duration_seconds}s exceeds max "
            f"{settings.audio_segment_max_seconds}s"
        )


def plan_segments_abc_default(
    track_duration_seconds: float,
    *,
    segment_duration_seconds: float | None = None,
    strategy: str = "abc_default",
) -> list[PlannedSegment]:
    if track_duration_seconds <= 0:
        raise SegmentValidationError("Track duration must be positive")

    requested = segment_duration_seconds or settings.audio_segment_default_seconds
    seg_dur = min(requested, settings.audio_segment_max_seconds, track_duration_seconds)
    validate_segment_duration(seg_dur)

    min_track_for_three = seg_dur * 2.5
    if track_duration_seconds < min_track_for_three:
        start = max(0.0, (track_duration_seconds - seg_dur) / 2.0)
        end = min(track_duration_seconds, start + seg_dur)
        duration = end - start
        validate_segment_duration(duration)
        return [
            PlannedSegment(
                segment_type="A",
                start_seconds=round(start, 3),
                end_seconds=round(end, 3),
                duration_seconds=round(duration, 3),
                strategy=strategy,
            )
        ]

    segments: list[PlannedSegment] = []
    for seg_type, zone_low, zone_high in ABC_ZONES:
        zone_start = track_duration_seconds * zone_low
        zone_end = track_duration_seconds * zone_high
        ideal_start = zone_start
        if ideal_start + seg_dur > track_duration_seconds:
            ideal_start = max(0.0, track_duration_seconds - seg_dur)
        if ideal_start < zone_start and zone_end - zone_start >= seg_dur * 0.5:
            ideal_start = zone_start
        start = max(0.0, min(ideal_start, track_duration_seconds - seg_dur))
        end = min(track_duration_seconds, start + seg_dur)
        duration = end - start
        if duration <= 0:
            continue
        validate_segment_duration(duration)
        segments.append(
            PlannedSegment(
                segment_type=seg_type,
                start_seconds=round(start, 3),
                end_seconds=round(end, 3),
                duration_seconds=round(duration, 3),
                strategy=strategy,
            )
        )

    if not segments:
        raise SegmentValidationError("Could not plan any valid segment")
    return segments


def plan_segments_for_track(
    track: TrackContext,
    strategy: str,
    *,
    segment_duration_seconds: float | None = None,
    analysis_mode: str = "fast",
    deezer_preview_available: bool = False,
    youtube_available: bool = False,
    youtube_confidence: float | None = None,
    deezer_match_confidence: float = 1.0,
) -> list[PlannedSegment]:
    duration_s = track.duration_ms / 1000.0
    if strategy == "abc_default":
        return plan_segments_abc_default(
            duration_s,
            segment_duration_seconds=segment_duration_seconds,
            strategy=strategy,
        )
    if strategy == "hybrid_deezer_youtube_representative":
        from app.audio.strategy.hybrid import plan_hybrid_segments

        plan = plan_hybrid_segments(
            duration_s,
            deezer_preview_available=deezer_preview_available,
            youtube_available=youtube_available,
            youtube_confidence=youtube_confidence,
            analysis_mode=analysis_mode,
            segment_duration_seconds=segment_duration_seconds,
            strategy=strategy,
            deezer_match_confidence=deezer_match_confidence,
        )
        return plan.segments
    raise ApiError(
        code="UNSUPPORTED_STRATEGY",
        message=f"Unknown segment strategy: {strategy}",
        status_code=400,
    )


def plan_hybrid_for_track(
    track: TrackContext,
    *,
    segment_duration_seconds: float | None = None,
    analysis_mode: str = "fast",
    deezer_preview_available: bool,
    youtube_available: bool,
    youtube_confidence: float | None = None,
    deezer_match_confidence: float = 1.0,
) -> tuple[list[PlannedSegment], str]:
    from app.audio.strategy.hybrid import plan_hybrid_segments

    duration_s = track.duration_ms / 1000.0
    plan = plan_hybrid_segments(
        duration_s,
        deezer_preview_available=deezer_preview_available,
        youtube_available=youtube_available,
        youtube_confidence=youtube_confidence,
        analysis_mode=analysis_mode,
        segment_duration_seconds=segment_duration_seconds,
        deezer_match_confidence=deezer_match_confidence,
    )
    return plan.segments, plan.analysis_decision
