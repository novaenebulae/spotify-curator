from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ModelStatus = Literal["available", "missing", "disabled"]


@dataclass(frozen=True)
class ClassifierSegmentOutput:
    model_key: str
    model_status: ModelStatus
    probability: float | None = None
    arousal: float | None = None
    valence: float | None = None
    voice_probability: float | None = None
    instrumental_probability: float | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class MappedFeature:
    feature_name: str
    value: float
    confidence: float
    model_key: str
    model_name: str | None = None
