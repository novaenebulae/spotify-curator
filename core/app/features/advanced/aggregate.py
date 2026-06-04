from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any

from app.features.advanced.mappers import map_segment_outputs_to_features
from app.features.advanced.raw_schemas import MappedFeature


@dataclass(frozen=True)
class AggregatedAdvancedFeature:
    feature_name: str
    value: float
    confidence: float
    model_key: str
    segments_used: int
    segments_total: int
    status: str


def _median(values: list[float]) -> float:
    if not values:
        raise ValueError("empty values")
    return float(statistics.median(values))


def aggregate_track_classifier_features(
    segment_outputs: list[dict[str, dict[str, Any]]],
) -> list[AggregatedAdvancedFeature]:
    """Aggregate per-segment classifier_outputs into track-level features."""
    if not segment_outputs:
        return []

    by_feature: dict[str, list[tuple[float, float, str]]] = {}
    segments_total = len(segment_outputs)

    for segment in segment_outputs:
        mapped = map_segment_outputs_to_features(segment)
        for mf in mapped:
            by_feature.setdefault(mf.feature_name, []).append(
                (mf.value, mf.confidence, mf.model_key)
            )

    aggregated: list[AggregatedAdvancedFeature] = []
    for feature_name, rows in by_feature.items():
        values = [r[0] for r in rows]
        confidences = [r[1] for r in rows]
        model_key = rows[0][2]
        segments_used = len(values)
        coverage = segments_used / segments_total if segments_total else 0.0
        conf = min(1.0, _median(confidences) * coverage)
        status = "success" if coverage >= 1.0 else "partial" if coverage > 0 else "missing"
        aggregated.append(
            AggregatedAdvancedFeature(
                feature_name=feature_name,
                value=_median(values),
                confidence=conf,
                model_key=model_key,
                segments_used=segments_used,
                segments_total=segments_total,
                status=status,
            )
        )
    return aggregated
