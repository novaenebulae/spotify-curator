from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass
from typing import Any

_logger = logging.getLogger(__name__)

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
        meta = self._mm.read_metadata(spec.head_key) or {}
        meta_classes = meta.get("classes") if isinstance(meta.get("classes"), list) else []
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
            base["arousal"], base["valence"] = _arousal_valence_scores(
                activations, meta_classes
            )
        elif spec.kind == "two_class":
            voice = _positive_score(activations, spec.positive_label or "voice")
            base["voice_probability"] = voice
            base["instrumental_probability"] = _label_score(
                scores, "instrumental", default=1.0 - voice
            )
        elif spec.kind == "regression_unit":
            base["probability"] = _regression_unit_score(activations, spec.head_key)
        else:  # binary
            base["probability"] = _binary_positive_probability(
                activations, spec.positive_label, meta_classes
            )
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


def _regression_unit_score(
    activations: list[tuple[str, float]], head_key: str
) -> float:
    """EffNet regression heads: single scalar, map logits to [0, 1] when needed."""
    if not activations:
        return 0.0
    raw: float | None = None
    if len(activations) == 1:
        raw = float(activations[0][1])
    else:
        for label, score in activations:
            if label.lower() in ("score", "value", "regression", head_key.lower()):
                raw = float(score)
                break
        if raw is None:
            raw = float(activations[0][1])
    if raw is None:
        return 0.0
    return _normalize_unit_score(raw)


def _sigmoid_regression(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _normalize_unit_score(raw: float) -> float:
    """Map logits or probabilities into [0, 1]."""
    if 0.0 <= raw <= 1.0:
        return float(raw)
    return _sigmoid_regression(raw)


def _binary_positive_probability(
    activations: list[tuple[str, float]],
    positive_label: str | None,
    meta_classes: list,
) -> float:
    """Pick the positive-class probability using manifest metadata class order."""
    if not activations:
        return 0.0
    classes = [str(c) for c in meta_classes] if meta_classes else []
    if positive_label and classes:
        for label, score in activations:
            if label.lower() == positive_label.lower():
                return _normalize_unit_score(float(score))
        act_labels = [str(a[0]) for a in activations]
        if len(act_labels) == len(classes) and all(
            act_labels[i].lower() == classes[i].lower() for i in range(len(classes))
        ):
            try:
                idx = next(
                    i for i, c in enumerate(classes) if c.lower() == positive_label.lower()
                )
                if idx < len(activations):
                    return _normalize_unit_score(float(activations[idx][1]))
            except StopIteration:
                pass
    fallback = _positive_score(activations, positive_label, "")
    return _normalize_unit_score(fallback)


def _arousal_valence_scores(
    activations: list[tuple[str, float]], meta_classes: list
) -> tuple[float, float]:
    scores = dict(activations)
    arousal = _label_score(scores, "arousal", default=-999.0)
    valence = _label_score(scores, "valence", default=-999.0)
    if arousal > -998 and valence > -998 and arousal != valence:
        return float(arousal), float(valence)
    classes = [str(c) for c in meta_classes] if meta_classes else []
    if len(activations) >= 2 and classes:
        a_idx = next((i for i, c in enumerate(classes) if "arousal" in c.lower()), 0)
        v_idx = next((i for i, c in enumerate(classes) if "valence" in c.lower()), 1)
        if a_idx < len(activations) and v_idx < len(activations):
            return float(activations[a_idx][1]), float(activations[v_idx][1])
    if len(activations) >= 2:
        return float(activations[0][1]), float(activations[1][1])
    fallback = _max_score(activations)
    return fallback, fallback


def _positive_score(
    activations: list[tuple[str, float]],
    positive_label: str | None,
    head_key: str = "",
) -> float:
    if not activations:
        return 0.0
    if positive_label is not None:
        for label, score in activations:
            if label.lower() == positive_label.lower():
                return float(score)
        for label, score in activations:
            if positive_label.lower() in label.lower():
                return float(score)
    if len(activations) == 1:
        return float(activations[0][1])
    _logger.warning(
        "classifier %s: positive_label=%r not in activations, using max score",
        head_key or "?",
        positive_label,
    )
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
