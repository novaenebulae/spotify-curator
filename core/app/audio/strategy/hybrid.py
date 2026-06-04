from __future__ import annotations

from dataclasses import dataclass

from app.audio.provider import PlannedSegment
from app.audio.segments import SegmentValidationError, validate_segment_duration
from app.settings.config import settings

ANALYSIS_DEEZER_PLUS_YT_2 = "deezer_plus_youtube_2_segments"
ANALYSIS_YT_THREE = "youtube_3_segments"
ANALYSIS_DEEZER_ONLY = "deezer_only"
ANALYSIS_YT_ONE = "youtube_1_segment"
ANALYSIS_UNAVAILABLE = "local_analysis_unavailable"

SOURCE_QUALITY_REPRESENTATIVE = "youtube_representative"
SOURCE_QUALITY_FALLBACK_THREE = "youtube_fallback_three_segments"
SOURCE_QUALITY_DEEZER = "deezer_preview_30s"


@dataclass(frozen=True)
class HybridPlan:
    segments: list[PlannedSegment]
    analysis_decision: str


def _center_segment(
    track_duration_s: float,
    *,
    center_fraction: float,
    segment_type: str,
    seg_dur: float,
    strategy: str,
    source: str,
    source_quality: str,
    analysis_decision: str,
    match_confidence: float = 1.0,
) -> PlannedSegment:
    center = track_duration_s * center_fraction
    start = max(0.0, center - seg_dur / 2.0)
    end = min(track_duration_s, start + seg_dur)
    start = max(0.0, end - seg_dur)
    duration = end - start
    validate_segment_duration(duration)
    return PlannedSegment(
        segment_type=segment_type,
        start_seconds=round(start, 3),
        end_seconds=round(end, 3),
        duration_seconds=round(duration, 3),
        strategy=strategy,
        source=source,
        source_quality=source_quality,
        match_confidence=match_confidence,
        analysis_decision=analysis_decision,
    )


def plan_hybrid_segments(
    track_duration_s: float,
    *,
    deezer_preview_available: bool,
    youtube_confidence: float | None,
    youtube_available: bool,
    analysis_mode: str = "fast",
    segment_duration_seconds: float | None = None,
    strategy: str = "hybrid_deezer_youtube_representative",
    deezer_match_confidence: float = 1.0,
) -> HybridPlan:
    if track_duration_s <= 0:
        raise SegmentValidationError("Track duration must be positive")

    requested = segment_duration_seconds or settings.audio_segment_default_seconds
    seg_dur = min(requested, settings.audio_segment_max_seconds, track_duration_s)
    validate_segment_duration(seg_dur)

    yt_conf = youtube_confidence if youtube_confidence is not None else 0.0
    mode = (analysis_mode or "fast").lower()

    if mode not in ("fast", "precise"):
        mode = "fast"

    if mode == "fast":
        # Prefer Deezer preview when available & confident enough.
        if deezer_preview_available:
            # Full Deezer preview (~30s) for MAEST/genre models; do not cap to 15s default.
            preview_dur = min(settings.audio_segment_max_seconds, 30.0)
            validate_segment_duration(preview_dur)
            seg = PlannedSegment(
                segment_type="DEEZER_PREVIEW",
                start_seconds=0.0,
                end_seconds=preview_dur,
                duration_seconds=preview_dur,
                strategy=strategy,
                source="deezer_preview",
                source_quality=SOURCE_QUALITY_DEEZER,
                match_confidence=deezer_match_confidence,
                analysis_decision=ANALYSIS_DEEZER_ONLY,
            )
            return HybridPlan(segments=[seg], analysis_decision=ANALYSIS_DEEZER_ONLY)
        if youtube_available:
            seg = _center_segment(
                track_duration_s,
                center_fraction=1 / 2,
                segment_type="YOUTUBE_1_2",
                seg_dur=seg_dur,
                strategy=strategy,
                source="youtube",
                source_quality=SOURCE_QUALITY_REPRESENTATIVE,
                analysis_decision=ANALYSIS_YT_ONE,
                match_confidence=yt_conf,
            )
            return HybridPlan(segments=[seg], analysis_decision=ANALYSIS_YT_ONE)
        return HybridPlan(segments=[], analysis_decision=ANALYSIS_UNAVAILABLE)

    # precise
    if deezer_preview_available and youtube_available:
        preview_dur = min(seg_dur, settings.audio_segment_max_seconds, 30.0)
        validate_segment_duration(preview_dur)
        deezer_seg = PlannedSegment(
            segment_type="DEEZER_PREVIEW",
            start_seconds=0.0,
            end_seconds=preview_dur,
            duration_seconds=preview_dur,
            strategy=strategy,
            source="deezer_preview",
            source_quality=SOURCE_QUALITY_DEEZER,
            match_confidence=deezer_match_confidence,
            analysis_decision=ANALYSIS_DEEZER_PLUS_YT_2,
        )
        segments = [
            deezer_seg,
            _center_segment(
                track_duration_s,
                center_fraction=1 / 3,
                segment_type="YOUTUBE_1_3",
                seg_dur=seg_dur,
                strategy=strategy,
                source="youtube",
                source_quality=SOURCE_QUALITY_REPRESENTATIVE,
                analysis_decision=ANALYSIS_DEEZER_PLUS_YT_2,
                match_confidence=yt_conf,
            ),
            _center_segment(
                track_duration_s,
                center_fraction=2 / 3,
                segment_type="YOUTUBE_2_3",
                seg_dur=seg_dur,
                strategy=strategy,
                source="youtube",
                source_quality=SOURCE_QUALITY_REPRESENTATIVE,
                analysis_decision=ANALYSIS_DEEZER_PLUS_YT_2,
                match_confidence=yt_conf,
            ),
        ]
        return HybridPlan(segments=segments, analysis_decision=ANALYSIS_DEEZER_PLUS_YT_2)

    if youtube_available:
        fractions = ((1 / 4, "YOUTUBE_1_4"), (1 / 2, "YOUTUBE_1_2"), (3 / 4, "YOUTUBE_3_4"))
        segments = [
            _center_segment(
                track_duration_s,
                center_fraction=frac,
                segment_type=stype,
                seg_dur=seg_dur,
                strategy=strategy,
                source="youtube",
                source_quality=SOURCE_QUALITY_FALLBACK_THREE,
                analysis_decision=ANALYSIS_YT_THREE,
                match_confidence=yt_conf,
            )
            for frac, stype in fractions
        ]
        return HybridPlan(segments=segments, analysis_decision=ANALYSIS_YT_THREE)

    if deezer_preview_available:
        preview_dur = min(seg_dur, settings.audio_segment_max_seconds, 30.0)
        validate_segment_duration(preview_dur)
        seg = PlannedSegment(
            segment_type="DEEZER_PREVIEW",
            start_seconds=0.0,
            end_seconds=preview_dur,
            duration_seconds=preview_dur,
            strategy=strategy,
            source="deezer_preview",
            source_quality=SOURCE_QUALITY_DEEZER,
            match_confidence=deezer_match_confidence,
            analysis_decision=ANALYSIS_DEEZER_ONLY,
        )
        return HybridPlan(segments=[seg], analysis_decision=ANALYSIS_DEEZER_ONLY)

    return HybridPlan(segments=[], analysis_decision=ANALYSIS_UNAVAILABLE)
