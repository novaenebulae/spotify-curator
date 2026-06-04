from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.features.advanced.mappers import classifier_model_keys
from app.models_registry import ModelRegistry
from app.models_registry.types import ModelStatus

_CLASSIFIER_TASK_TYPES = frozenset({"mood", "classifier"})


def _deterministic_probability(segment_id: int, model_key: str) -> float:
    digest = hashlib.sha256(f"{segment_id}:{model_key}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


@dataclass(frozen=True)
class ClassifierRunResult:
    classifier_outputs: dict[str, dict[str, Any]]
    models_missing: list[str]
    inference_mode: str


class ClassifierRunner:
    """Stub classifier inference (phase 6.7) until real Essentia TF is wired."""

    def __init__(self, *, registry: ModelRegistry | None = None) -> None:
        self._registry = registry or ModelRegistry()

    def run_for_segment(self, *, segment_id: int, wav_path: str) -> ClassifierRunResult:
        del wav_path  # real inference uses segment audio in a later phase
        statuses, _ = self._registry.scan()
        by_key = {s.model_key: s for s in statuses}
        outputs: dict[str, dict[str, Any]] = {}
        missing: list[str] = []

        for model_key in sorted(classifier_model_keys()):
            status = by_key.get(model_key)
            if status is None or not _is_available_classifier(status):
                missing.append(model_key)
                continue
            outputs[model_key] = _stub_output(segment_id, model_key)

        return ClassifierRunResult(
            classifier_outputs=outputs,
            models_missing=missing,
            inference_mode="stub",
        )


def _is_available_classifier(status: ModelStatus) -> bool:
    if status.task_type not in _CLASSIFIER_TASK_TYPES:
        return False
    return status.status == "available"


def _stub_output(segment_id: int, model_key: str) -> dict[str, Any]:
    prob = _deterministic_probability(segment_id, model_key)
    base: dict[str, Any] = {
        "model_key": model_key,
        "model_status": "available",
        "probability": prob,
    }
    if model_key == "arousal_valence":
        base = {
            "model_key": model_key,
            "model_status": "available",
            "arousal": prob * 2.0 - 1.0,
            "valence": (1.0 - prob) * 2.0 - 1.0,
        }
    elif model_key == "voice_instrumental":
        base = {
            "model_key": model_key,
            "model_status": "available",
            "voice_probability": prob,
            "instrumental_probability": 1.0 - prob,
        }
    return base
