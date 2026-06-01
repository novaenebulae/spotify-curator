from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldConfidence:
    value: float | int | None
    confidence: float | None


@dataclass(frozen=True)
class ConfidenceResult:
    fields: dict[str, FieldConfidence]
    feature_confidence: float
    status: str


FEATURE_FIELD_NAMES = (
    "bpm",
    "energy",
    "danceability",
    "valence",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "liveness",
    "loudness",
    "key",
    "mode",
    "time_signature",
    "duration_ms",
)

_FLOAT_0_1_FIELDS = frozenset(
    {
        "energy",
        "danceability",
        "valence",
        "acousticness",
        "instrumentalness",
        "speechiness",
        "liveness",
    }
)


def _is_valid_float(value: Any, *, low: float | None = None, high: float | None = None) -> bool:
    if value is None:
        return False
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    if low is not None and f < low:
        return False
    if high is not None and f > high:
        return False
    return True


def _is_valid_int(value: Any, *, low: int | None = None, high: int | None = None) -> bool:
    if value is None:
        return False
    try:
        i = int(value)
    except (TypeError, ValueError):
        return False
    if low is not None and i < low:
        return False
    if high is not None and i > high:
        return False
    return True


def _fc_float(value: Any, valid: bool, match_confidence: float) -> FieldConfidence:
    conf = match_confidence if valid else None
    parsed = float(value) if valid else None
    return FieldConfidence(value=parsed, confidence=conf)


def _fc_int(value: Any, valid: bool, match_confidence: float) -> FieldConfidence:
    conf = match_confidence if valid else None
    parsed = int(value) if valid else None
    return FieldConfidence(value=parsed, confidence=conf)


def field_confidence(
    name: str,
    value: Any,
    *,
    match_confidence: float = 1.0,
) -> FieldConfidence:
    if name == "bpm":
        valid = _is_valid_float(value, low=0)
        return _fc_float(value, valid, match_confidence)
    if name in _FLOAT_0_1_FIELDS:
        valid = _is_valid_float(value, low=0, high=1)
        return _fc_float(value, valid, match_confidence)
    if name == "loudness":
        valid = _is_valid_float(value)
        return _fc_float(value, valid, match_confidence)
    if name == "key":
        valid = _is_valid_int(value, low=0, high=11)
        return _fc_int(value, valid, match_confidence)
    if name == "mode":
        valid = _is_valid_int(value, low=0, high=1)
        return _fc_int(value, valid, match_confidence)
    if name == "time_signature":
        valid = _is_valid_int(value, low=0)
        return _fc_int(value, valid, match_confidence)
    if name == "duration_ms":
        valid = _is_valid_int(value, low=0)
        return _fc_int(value, valid, match_confidence)
    return FieldConfidence(value=value, confidence=None)


def compute_match_confidence(*, isrc_match: bool, spotify_id_match: bool) -> float:
    if isrc_match:
        return 1.0
    if spotify_id_match:
        return 0.9
    return 0.5


def aggregate_confidence(fields: dict[str, FieldConfidence]) -> tuple[float, str]:
    confidences = [
        f.confidence
        for f in fields.values()
        if f.confidence is not None and f.value is not None
    ]
    if not confidences:
        return 0.0, "failed"
    avg = sum(confidences) / len(confidences)
    present = sum(1 for f in fields.values() if f.value is not None)
    total = len(FEATURE_FIELD_NAMES)
    if present == total:
        return avg, "success"
    if present > 0:
        return avg, "partial"
    return 0.0, "failed"
