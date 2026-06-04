from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedSegmentFeatures:
    bpm: float | None = None
    bpm_confidence: float | None = None
    loudness: float | None = None
    key: int | None = None
    mode: int | None = None
    key_confidence: float | None = None
    duration_ms: int | None = None
    mfcc: list[float] = field(default_factory=list)
    hpcp: list[float] = field(default_factory=list)
    spectral_centroid: float | None = None
    spectral_rolloff: float | None = None
    spectral_contrast: list[float] = field(default_factory=list)
    dynamic_complexity: float | None = None
    onset_rate: float | None = None
    beats_count: int | None = None
    raw_summary: dict[str, Any] = field(default_factory=dict)
    source_quality: str | None = None
    source_quality_weight: float = 1.0
    match_confidence: float = 1.0


_KEY_MAP = {
    "c": 0,
    "c#": 1,
    "db": 1,
    "d": 2,
    "d#": 3,
    "eb": 3,
    "e": 4,
    "f": 5,
    "f#": 6,
    "gb": 6,
    "g": 7,
    "g#": 8,
    "ab": 8,
    "a": 9,
    "a#": 10,
    "bb": 10,
    "b": 11,
}


def _dig(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _mean_value(node: Any) -> float | None:
    if isinstance(node, (int, float)):
        return float(node)
    if isinstance(node, dict):
        if "mean" in node:
            m = node["mean"]
            if isinstance(m, (int, float)):
                return float(m)
            if isinstance(m, list) and m:
                return float(sum(float(x) for x in m) / len(m))
        for k in ("value", "avg", "average"):
            if k in node and isinstance(node[k], (int, float)):
                return float(node[k])
    if isinstance(node, list) and node:
        nums = [float(x) for x in node if isinstance(x, (int, float))]
        if nums:
            return sum(nums) / len(nums)
    return None


def _parse_key_mode(tonal: dict[str, Any]) -> tuple[int | None, int | None, float | None]:
    key_name = tonal.get("key_key") or tonal.get("key")
    scale = tonal.get("key_scale") or tonal.get("scale")
    strength = tonal.get("key_strength") or tonal.get("key_confidence")
    for profile in ("key_edma", "key_krumhansl", "key_temperley"):
        block = tonal.get(profile)
        if isinstance(block, dict):
            key_name = key_name or block.get("key")
            scale = scale or block.get("scale")
            strength = strength or block.get("strength")
            break
    if isinstance(key_name, str):
        k = _KEY_MAP.get(key_name.lower().strip())
    elif isinstance(key_name, int):
        k = key_name
    else:
        k = None
    mode = None
    if isinstance(scale, str):
        sl = scale.lower()
        if sl in ("major", "maj"):
            mode = 1
        elif sl in ("minor", "min"):
            mode = 0
    elif isinstance(scale, int):
        mode = scale
    conf = float(strength) if isinstance(strength, (int, float)) else None
    return k, mode, conf


def parse_essentia_json(payload: dict[str, Any]) -> ParsedSegmentFeatures:
    tonal = payload.get("tonal") if isinstance(payload.get("tonal"), dict) else {}
    rhythm = payload.get("rhythm") if isinstance(payload.get("rhythm"), dict) else {}
    low = payload.get("lowlevel") if isinstance(payload.get("lowlevel"), dict) else {}

    bpm = rhythm.get("bpm")
    if bpm is None:
        bpm = _dig(payload, "rhythm", "bpm")
    bpm_f = float(bpm) if isinstance(bpm, (int, float)) else _mean_value(bpm)

    loudness = low.get("loudness") or low.get("average_loudness")
    if loudness is None:
        loudness = _dig(payload, "lowlevel", "loudness") or _dig(payload, "lowlevel", "average_loudness")
    loudness_f = float(loudness) if isinstance(loudness, (int, float)) else _mean_value(loudness)

    key, mode, key_conf = _parse_key_mode(tonal)
    length = _dig(payload, "metadata", "audio_properties", "length")
    duration_ms = int(float(length) * 1000) if isinstance(length, (int, float)) else None

    tonal_hpcp = tonal.get("hpcp") if isinstance(tonal.get("hpcp"), dict) else None
    mfcc_node = low.get("mfcc") or _dig(payload, "lowlevel", "mfcc")
    hpcp_node = low.get("hpcp") or tonal_hpcp or _dig(payload, "tonal", "hpcp") or _dig(payload, "lowlevel", "hpcp")
    mfcc_mean = _mean_value(mfcc_node)
    mfcc_list: list[float] = []
    if isinstance(mfcc_node, dict) and isinstance(mfcc_node.get("mean"), list):
        mfcc_list = [float(x) for x in mfcc_node["mean"]]
    elif mfcc_mean is not None:
        mfcc_list = [mfcc_mean]

    hpcp_list: list[float] = []
    if isinstance(hpcp_node, dict) and isinstance(hpcp_node.get("mean"), list):
        hpcp_list = [float(x) for x in hpcp_node["mean"]]

    contrast_node = low.get("spectral_contrast") or _dig(payload, "lowlevel", "spectral_contrast")
    contrast_list: list[float] = []
    if isinstance(contrast_node, dict) and isinstance(contrast_node.get("mean"), list):
        contrast_list = [float(x) for x in contrast_node["mean"]]

    return ParsedSegmentFeatures(
        bpm=bpm_f,
        bpm_confidence=0.85 if bpm_f else None,
        loudness=loudness_f,
        key=key,
        mode=mode,
        key_confidence=key_conf,
        duration_ms=duration_ms,
        mfcc=mfcc_list,
        hpcp=hpcp_list,
        spectral_centroid=_mean_value(low.get("spectral_centroid") or _dig(payload, "lowlevel", "spectral_centroid")),
        spectral_rolloff=_mean_value(low.get("spectral_rolloff") or _dig(payload, "lowlevel", "spectral_rolloff")),
        spectral_contrast=contrast_list,
        dynamic_complexity=_mean_value(
            low.get("dynamic_complexity") or _dig(payload, "lowlevel", "dynamic_complexity")
        ),
        onset_rate=_mean_value(low.get("onset_rate") or rhythm.get("onset_rate")),
        beats_count=int(rhythm["beats_count"])
        if isinstance(rhythm.get("beats_count"), (int, float))
        else None,
        raw_summary={
            "bpm": bpm_f,
            "key": key,
            "mode": mode,
            "loudness": loudness_f,
        },
    )


def parse_essentia_json_file(path: str) -> ParsedSegmentFeatures:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Essentia JSON root must be an object")
    return parse_essentia_json(data)


def parsed_segment_to_storage_dict(parsed: ParsedSegmentFeatures) -> dict[str, Any]:
    return {
        "bpm": parsed.bpm,
        "bpm_confidence": parsed.bpm_confidence,
        "loudness": parsed.loudness,
        "key": parsed.key,
        "mode": parsed.mode,
        "key_confidence": parsed.key_confidence,
        "duration_ms": parsed.duration_ms,
        "mfcc": parsed.mfcc,
        "hpcp": parsed.hpcp,
        "spectral_centroid": parsed.spectral_centroid,
        "spectral_rolloff": parsed.spectral_rolloff,
        "spectral_contrast": parsed.spectral_contrast,
        "dynamic_complexity": parsed.dynamic_complexity,
        "onset_rate": parsed.onset_rate,
        "beats_count": parsed.beats_count,
        "raw_summary": parsed.raw_summary,
        "source_quality": parsed.source_quality,
        "source_quality_weight": parsed.source_quality_weight,
        "match_confidence": parsed.match_confidence,
    }


def parsed_segment_from_storage(payload: dict[str, Any]) -> ParsedSegmentFeatures:
    if "raw_summary" in payload and "mfcc" not in payload and len(payload) <= 6:
        return ParsedSegmentFeatures(
            bpm=payload.get("bpm"),
            loudness=payload.get("loudness"),
            key=payload.get("key"),
            mode=payload.get("mode"),
            raw_summary=dict(payload),
        )
    return ParsedSegmentFeatures(
        bpm=payload.get("bpm"),
        bpm_confidence=payload.get("bpm_confidence"),
        loudness=payload.get("loudness"),
        key=payload.get("key"),
        mode=payload.get("mode"),
        key_confidence=payload.get("key_confidence"),
        duration_ms=payload.get("duration_ms"),
        mfcc=list(payload.get("mfcc") or []),
        hpcp=list(payload.get("hpcp") or []),
        spectral_centroid=payload.get("spectral_centroid"),
        spectral_rolloff=payload.get("spectral_rolloff"),
        spectral_contrast=list(payload.get("spectral_contrast") or []),
        dynamic_complexity=payload.get("dynamic_complexity"),
        onset_rate=payload.get("onset_rate"),
        beats_count=payload.get("beats_count"),
        raw_summary=dict(payload.get("raw_summary") or {}),
        source_quality=payload.get("source_quality"),
        source_quality_weight=float(payload.get("source_quality_weight") or 1.0),
        match_confidence=float(payload.get("match_confidence") or 1.0),
    )


def parsed_segment_from_features_json(features_json: str) -> ParsedSegmentFeatures:
    data = json.loads(features_json)
    if not isinstance(data, dict):
        raise ValueError("features_json must be a JSON object")
    return parsed_segment_from_storage(data)
