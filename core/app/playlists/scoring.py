from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.playlists.feature_registry import FeatureRegistry, get_feature_registry
from app.playlists.rule_schemas import PlaylistRule
from app.playlists.types import TrackFeatureView


@dataclass
class ScoreResult:
    track_id: int
    final_score: float
    score_details: dict[str, Any]
    excluded: bool = False
    exclusion_code: str | None = None


def score_tracks(
    rule: PlaylistRule,
    views: dict[int, TrackFeatureView],
    *,
    registry: FeatureRegistry | None = None,
) -> tuple[list[ScoreResult], list[str]]:
    reg = registry or get_feature_registry()
    results: list[ScoreResult] = []
    warnings: list[str] = []

    for tid in sorted(views.keys()):
        view = views[tid]
        sr, w = _score_one(rule, view, reg)
        results.append(sr)
        warnings.extend(w)

    return results, warnings


def _score_one(
    rule: PlaylistRule,
    view: TrackFeatureView,
    registry: FeatureRegistry,
) -> tuple[ScoreResult, list[str]]:
    warnings: list[str] = []
    components_out: dict[str, Any] = {}
    contributions: list[tuple[str, float, float, float]] = []

    for name, spec in rule.weights.components.items():
        canonical = registry.resolve_name(name)
        if registry.is_future(canonical):
            components_out[name] = {
                "value": None,
                "initial_weight": spec.weight,
                "effective_weight": 0.0,
                "contribution": 0.0,
                "skipped": True,
                "warning": "FEATURE_NOT_AVAILABLE_YET",
            }
            warnings.append("FEATURE_NOT_AVAILABLE_YET")
            continue

        norm_value, source, confidence, skipped, warn = _component_value(
            name, canonical, view, registry
        )
        if warn:
            warnings.append(warn)
        if skipped or norm_value is None:
            components_out[name] = {
                "value": None,
                "initial_weight": spec.weight,
                "effective_weight": 0.0,
                "contribution": 0.0,
                "skipped": True,
                "warning": warn,
            }
            continue
        contributions.append((name, norm_value, spec.weight, confidence or 1.0))
        components_out[name] = {
            "value": norm_value,
            "initial_weight": spec.weight,
            "effective_weight": 0.0,
            "contribution": 0.0,
            "source": source,
            "confidence": confidence,
            "skipped": False,
        }

    if not contributions:
        return (
            ScoreResult(
                track_id=view.track_id,
                final_score=0.0,
                score_details={
                    "final_score": 0.0,
                    "components": components_out,
                    "warnings": list(set(warnings)),
                    "engine_version": registry.ENGINE_VERSION,
                },
                excluded=True,
                exclusion_code="SCORE_NOT_COMPUTABLE",
            ),
            warnings,
        )

    weight_sum = sum(w for _, _, w, _ in contributions)
    final = 0.0
    for name, norm_value, initial_w, _conf in contributions:
        effective_w = initial_w / weight_sum if weight_sum > 0 else 0.0
        contrib = norm_value * effective_w
        final += contrib
        components_out[name]["effective_weight"] = round(effective_w, 6)
        components_out[name]["contribution"] = round(contrib, 6)

    final = max(0.0, min(1.0, final))
    details = {
        "final_score": round(final, 6),
        "components": components_out,
        "warnings": list(set(warnings)),
        "engine_version": registry.ENGINE_VERSION,
    }
    return (
        ScoreResult(
            track_id=view.track_id,
            final_score=final,
            score_details=details,
        ),
        warnings,
    )


def _component_value(
    name: str,
    canonical: str,
    view: TrackFeatureView,
    registry: FeatureRegistry,
) -> tuple[float | None, str | None, float | None, bool, str | None]:
    if name == "valence_inverse" or canonical == "valence" and name == "valence_inverse":
        fv = view.features.get("valence_inverse")
        if fv and fv.value is not None:
            return float(fv.value), fv.source, fv.confidence, False, None
    if name == "freshness_score":
        liked = view.features.get("liked_status")
        return (0.5 if liked and liked.value else 0.3, "derived", 0.5, False, None)
    if name == "playlist_fit_score":
        return (0.5, "derived", 0.5, False, None)
    if name == "diversity_bonus":
        return (0.1, "derived", 0.5, False, None)
    if name == "preview_bonus":
        pv = view.features.get("preview_available")
        if pv and pv.value:
            return (0.05, "track_previews", 1.0, False, None)
        return (0.0, "track_previews", 1.0, False, None)

    fv = view.features.get(canonical)
    if fv is None or fv.status == "not_available_yet":
        return None, None, None, True, "FEATURE_NOT_AVAILABLE_YET"
    if fv.value is None or fv.status in ("missing", "low_confidence"):
        return None, fv.source, fv.confidence, True, fv.missing_reason

    val = float(fv.value)
    desc = registry.get(canonical)
    if desc and desc.range_min is not None and desc.range_max is not None:
        span = desc.range_max - desc.range_min
        if span > 0:
            val = (val - desc.range_min) / span
    val = max(0.0, min(1.0, val))
    return val, fv.source, fv.confidence, False, None


def score_details_json(result: ScoreResult) -> str:
    return json.dumps(result.score_details)
