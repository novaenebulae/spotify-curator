from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GenreLabelScore:
    label: str
    score: float


@dataclass(frozen=True)
class AggregatedGenre:
    top_k: list[GenreLabelScore]
    top_label: str
    top_score: float
    segments_used: int
    status: str


_STUB_LABELS = (
    "Techno",
    "House",
    "Ambient",
    "Rock",
    "Pop",
    "Jazz",
    "Classical",
    "Hip-Hop",
    "Metal",
    "Folk",
)


def parse_genre_segment_output(payload: dict[str, Any]) -> list[GenreLabelScore]:
    top_k = payload.get("top_k")
    if not isinstance(top_k, list):
        return []
    out: list[GenreLabelScore] = []
    for item in top_k:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        score = item.get("score")
        if label is None or score is None:
            continue
        out.append(GenreLabelScore(label=str(label), score=float(score)))
    return out


def aggregate_genre_top_k(
    segment_top_k_lists: list[list[GenreLabelScore]],
) -> AggregatedGenre | None:
    """Median score per label across segments; rank by median descending."""
    if not segment_top_k_lists:
        return None

    by_label: dict[str, list[float]] = {}
    for top_k in segment_top_k_lists:
        for item in top_k:
            by_label.setdefault(item.label, []).append(item.score)

    merged: list[GenreLabelScore] = []
    for label, scores in by_label.items():
        merged.append(GenreLabelScore(label=label, score=float(statistics.median(scores))))

    merged.sort(key=lambda x: x.score, reverse=True)
    if not merged:
        return None

    top = merged[0]
    return AggregatedGenre(
        top_k=merged,
        top_label=top.label,
        top_score=top.score,
        segments_used=len(segment_top_k_lists),
        status="success",
    )


def genre_features_from_top_k(
    aggregated: AggregatedGenre,
    *,
    model_name: str,
    pipeline_version: str,
) -> list[dict[str, Any]]:
    """Rows ready for TrackAdvancedFeaturesRepository (feature_name + fields)."""
    top_k_json = json.dumps(
        [{"label": g.label, "score": g.score} for g in aggregated.top_k]
    )
    return [
        {
            "feature_name": "genre_discogs_519",
            "value_json": top_k_json,
            "value_float": None,
            "value_text": None,
            "source": "essentia_tensorflow",
            "model_name": model_name,
            "pipeline_version": pipeline_version,
            "aggregation_method": "median",
            "status": aggregated.status,
            "confidence": aggregated.top_score,
        },
        {
            "feature_name": "genre_discogs_519_top_label",
            "value_text": aggregated.top_label,
            "value_float": None,
            "value_json": None,
            "source": "essentia_tensorflow",
            "model_name": model_name,
            "pipeline_version": pipeline_version,
            "status": aggregated.status,
            "confidence": aggregated.top_score,
        },
        {
            "feature_name": "genre_discogs_519_top_score",
            "value_float": aggregated.top_score,
            "value_text": None,
            "value_json": None,
            "source": "essentia_tensorflow",
            "model_name": model_name,
            "pipeline_version": pipeline_version,
            "status": aggregated.status,
            "confidence": aggregated.top_score,
        },
        {
            "feature_name": "genre_discogs_519_top_k",
            "value_json": top_k_json,
            "value_float": None,
            "value_text": None,
            "source": "essentia_tensorflow",
            "model_name": model_name,
            "pipeline_version": pipeline_version,
            "status": aggregated.status,
            "confidence": aggregated.top_score,
        },
    ]


def stub_label_pool() -> tuple[str, ...]:
    return _STUB_LABELS
