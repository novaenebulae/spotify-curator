from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.audio.tensorflow.backend import TensorflowInferenceBackend, model_identity
from app.audio.tensorflow.guard import ensure_stub_allowed, stubs_allowed
from app.audio.tensorflow.model_map import ClassifierSpec, classifier_specs
from app.models_registry.manager import ModelManager


def _deterministic_probability(segment_id: int, model_key: str) -> float:
    digest = hashlib.sha256(f"{segment_id}:{model_key}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


@dataclass(frozen=True)
class ClassifierRunResult:
    classifier_outputs: dict[str, dict[str, Any]]
    models_missing: list[str]
    inference_mode: str


class ClassifierRunner:
    """Essentia TensorFlow classification heads (phase 6.8B).

    Real inference uses the injected backend; stubs are only produced inside the
    test environment (see :func:`stubs_allowed`).
    """

    def __init__(
        self,
        *,
        model_manager: ModelManager | None = None,
        backend: TensorflowInferenceBackend | None = None,
    ) -> None:
        self._mm = model_manager or ModelManager()
        self._backend = backend

    def run_for_segment(self, *, segment_id: int, wav_path: str) -> ClassifierRunResult:
        outputs: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        real_used = False
        stub_used = False

        for spec in sorted(classifier_specs(), key=lambda s: s.legacy_key):
            if not self._is_available(spec):
                missing.append(spec.legacy_key)
                continue
            if self._backend is not None:
                outputs[spec.legacy_key] = self._real_output(spec, wav_path)
                real_used = True
            elif stubs_allowed():
                outputs[spec.legacy_key] = _stub_output(segment_id, spec.legacy_key)
                stub_used = True
            else:
                ensure_stub_allowed(model_key=spec.legacy_key)

        return ClassifierRunResult(
            classifier_outputs=outputs,
            models_missing=missing,
            inference_mode=_resolve_mode(real_used, stub_used),
        )

    def _is_available(self, spec: ClassifierSpec) -> bool:
        return self._mm.is_available(spec.extractor_key) and self._mm.is_available(spec.head_key)

    def _real_output(self, spec: ClassifierSpec, wav_path: str) -> dict[str, Any]:
        assert self._backend is not None
        activations = self._backend.classifier_activations(
            wav_path, extractor_key=spec.extractor_key, head_key=spec.head_key
        )
        model_name, model_version = model_identity(self._mm, spec.head_key)
        base: dict[str, Any] = {
            "model_key": spec.legacy_key,
            "model_status": "available",
            "model_name": model_name,
            "model_version": model_version,
            "inference_mode": "real",
            "wav_path_used": True,
        }
        scores = dict(activations)
        if spec.kind == "arousal_valence":
            base["arousal"] = _label_score(scores, "arousal", default=_max_score(activations))
            base["valence"] = _label_score(scores, "valence", default=_max_score(activations))
        elif spec.kind == "two_class":
            voice = _positive_score(activations, spec.positive_label or "voice")
            base["voice_probability"] = voice
            base["instrumental_probability"] = _label_score(
                scores, "instrumental", default=1.0 - voice
            )
        else:  # binary
            base["probability"] = _positive_score(activations, spec.positive_label)
        return base


def _resolve_mode(real_used: bool, stub_used: bool) -> str:
    if real_used:
        return "real"
    if stub_used:
        return "stub"
    return "none"


def _max_score(activations: list[tuple[str, float]]) -> float:
    if not activations:
        return 0.0
    return float(max(score for _, score in activations))


def _label_score(scores: dict[str, float], label: str, *, default: float) -> float:
    for key, value in scores.items():
        if key.lower() == label.lower():
            return float(value)
    return float(default)


def _positive_score(activations: list[tuple[str, float]], positive_label: str | None) -> float:
    if not activations:
        return 0.0
    if positive_label is not None:
        for label, score in activations:
            if label.lower() == positive_label.lower():
                return float(score)
        for label, score in activations:
            if positive_label.lower() in label.lower():
                return float(score)
    # Regression heads expose a single output; fall back to it.
    if len(activations) == 1:
        return float(activations[0][1])
    return _max_score(activations)


def _stub_output(segment_id: int, model_key: str) -> dict[str, Any]:
    prob = _deterministic_probability(segment_id, model_key)
    base: dict[str, Any] = {
        "model_key": model_key,
        "model_status": "available",
        "probability": prob,
        "inference_mode": "stub",
    }
    if model_key == "arousal_valence":
        base = {
            "model_key": model_key,
            "model_status": "available",
            "arousal": prob * 2.0 - 1.0,
            "valence": (1.0 - prob) * 2.0 - 1.0,
            "inference_mode": "stub",
        }
    elif model_key == "voice_instrumental":
        base = {
            "model_key": model_key,
            "model_status": "available",
            "voice_probability": prob,
            "instrumental_probability": 1.0 - prob,
            "inference_mode": "stub",
        }
    return base
