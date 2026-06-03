from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from app.audio.confidence import compute_feature_confidence
from app.audio.essentia_parser import ParsedSegmentFeatures


@dataclass
class AggregatedFeatures:
    bpm: float | None = None
    bpm_confidence: float | None = None
    loudness: float | None = None
    key: int | None = None
    mode: int | None = None
    key_confidence: float | None = None
    duration_ms: int | None = None
    feature_confidence: float | None = None
    mfcc: list[float] = field(default_factory=list)
    hpcp: list[float] = field(default_factory=list)
    spectral_centroid: float | None = None
    spectral_rolloff: float | None = None
    spectral_contrast: list[float] = field(default_factory=list)
    dynamic_complexity: float | None = None
    onset_rate: float | None = None
    segments_used: int = 0
    segments_planned: int | None = None
    segments_analyzed: int | None = None
    segments_missing_reason: str | None = None
    detail_json: dict[str, Any] = field(default_factory=dict)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _weighted_mean(values: list[float], weights: list[float]) -> float | None:
    if not values or not weights:
        return None
    total_w = sum(weights)
    if total_w <= 0:
        return _mean(values)
    return float(sum(v * w for v, w in zip(values, weights, strict=True)) / total_w)


def _vote_key_mode(
    parsed: list[ParsedSegmentFeatures],
) -> tuple[int | None, int | None, float | None]:
    votes: dict[tuple[int, int], float] = {}
    for p in parsed:
        if p.key is None or p.mode is None:
            continue
        w = (p.key_confidence or 0.5) * p.source_quality_weight * p.match_confidence
        key = (p.key, p.mode)
        votes[key] = votes.get(key, 0.0) + w
    if not votes:
        return None, None, None
    best = max(votes.items(), key=lambda kv: kv[1])
    return best[0][0], best[0][1], best[1] / len(parsed)


def _mean_vectors(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    width = max(len(v) for v in vectors)
    out = []
    for i in range(width):
        vals = [v[i] for v in vectors if i < len(v)]
        m = _mean(vals)
        out.append(m if m is not None else 0.0)
    return out


def aggregate_segment_features(
    parsed: list[ParsedSegmentFeatures],
    *,
    analysis_decision: str | None = None,
    segments_planned: int | None = None,
    segments_missing_reason: str | None = None,
) -> AggregatedFeatures:
    if not parsed:
        return AggregatedFeatures(segments_used=0)
    weights = [p.source_quality_weight for p in parsed]
    parser_confs = [
        float(p.bpm_confidence or p.key_confidence or 0.85) for p in parsed
    ]
    match_confs = [float(p.match_confidence) for p in parsed]

    bpms = [(float(p.bpm), p.source_quality_weight * p.match_confidence) for p in parsed if p.bpm is not None]
    loudness = [
        (float(p.loudness), p.source_quality_weight * p.match_confidence)
        for p in parsed
        if p.loudness is not None
    ]
    key, mode, key_conf = _vote_key_mode(parsed)
    durations = [p.duration_ms for p in parsed if p.duration_ms is not None]

    bpm_val = _weighted_mean([b for b, _ in bpms], [w for _, w in bpms]) if bpms else None
    loud_val = _weighted_mean([x for x, _ in loudness], [w for _, w in loudness]) if loudness else None

    mfcc_vec = _mean_vectors([p.mfcc for p in parsed if p.mfcc])
    hpcp_vec = _mean_vectors([p.hpcp for p in parsed if p.hpcp])
    spectral_centroid_val = _median(
        [float(p.spectral_centroid) for p in parsed if p.spectral_centroid is not None]
    )
    spectral_rolloff_val = _median(
        [float(p.spectral_rolloff) for p in parsed if p.spectral_rolloff is not None]
    )
    spectral_contrast_vec = _mean_vectors([p.spectral_contrast for p in parsed if p.spectral_contrast])
    dynamic_complexity_val = _median(
        [float(p.dynamic_complexity) for p in parsed if p.dynamic_complexity is not None]
    )
    onset_rate_val = _median([float(p.onset_rate) for p in parsed if p.onset_rate is not None])

    segments_missing = None
    if segments_planned is not None and segments_planned > len(parsed):
        segments_missing = segments_missing_reason or "not_all_segments_available"

    detail: dict[str, Any] = {
        "segment_count": len(parsed),
        "segments_analyzed": len(parsed),
        "mfcc": mfcc_vec,
        "hpcp": hpcp_vec,
        "spectral_centroid": spectral_centroid_val,
        "spectral_rolloff": spectral_rolloff_val,
        "spectral_contrast": spectral_contrast_vec,
        "dynamic_complexity": dynamic_complexity_val,
        "onset_rate": onset_rate_val,
        "source_qualities": [p.source_quality for p in parsed],
        "source_quality_weights": weights,
        "match_confidences": match_confs,
    }
    if segments_planned is not None:
        detail["segments_planned"] = segments_planned
        if segments_missing:
            detail["segments_missing_reason"] = segments_missing
    if analysis_decision:
        detail["analysis_decision"] = analysis_decision

    return AggregatedFeatures(
        bpm=bpm_val,
        bpm_confidence=_mean([float(p.bpm_confidence or 0.85) for p in parsed if p.bpm is not None]),
        loudness=loud_val,
        key=key,
        mode=mode,
        key_confidence=key_conf,
        duration_ms=int(statistics.median(durations)) if durations else None,
        feature_confidence=compute_feature_confidence(
            parser_confs,
            source_quality_weights=weights,
            match_confidences=match_confs,
        ),
        mfcc=mfcc_vec,
        hpcp=hpcp_vec,
        spectral_centroid=spectral_centroid_val,
        spectral_rolloff=spectral_rolloff_val,
        spectral_contrast=spectral_contrast_vec,
        dynamic_complexity=dynamic_complexity_val,
        onset_rate=onset_rate_val,
        segments_used=len(parsed),
        segments_planned=segments_planned,
        segments_analyzed=len(parsed),
        segments_missing_reason=segments_missing,
        detail_json=detail,
    )
