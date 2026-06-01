from __future__ import annotations

from app.settings.config import settings


def source_quality_weight(source_quality: str | None) -> float:
    if source_quality == "youtube_representative":
        return settings.confidence_weight_youtube_representative
    if source_quality == "youtube_fallback_three_segments":
        return settings.confidence_weight_youtube_fallback_three
    if source_quality == "deezer_preview_30s":
        return settings.confidence_weight_deezer_preview_only
    return 1.0


def compute_feature_confidence(
    parser_confidences: list[float],
    *,
    source_quality_weights: list[float],
    match_confidences: list[float],
) -> float | None:
    if not parser_confidences:
        return None
    pc = sum(parser_confidences) / len(parser_confidences)
    sq = sum(source_quality_weights) / len(source_quality_weights) if source_quality_weights else 1.0
    mc = sum(match_confidences) / len(match_confidences) if match_confidences else 1.0
    return round(pc * sq * mc, 4)
