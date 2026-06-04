from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.audio.tensorflow.backend import TensorflowInferenceBackend, model_identity
from app.audio.tensorflow.guard import ensure_stub_allowed, stubs_allowed
from app.audio.tensorflow.model_map import (
    GENRE_EXTRACTOR_KEY,
    GENRE_HEAD_KEY,
    GENRE_LEGACY_KEY,
)
from app.features.embeddings.genre_discogs import stub_label_pool
from app.models_registry.manager import ModelManager
from app.settings.config import settings

GENRE_MODEL_KEY = GENRE_LEGACY_KEY


def _deterministic_top_k(segment_id: int, *, k: int) -> list[dict[str, float | str]]:
    labels = stub_label_pool()
    scored: list[tuple[str, float]] = []
    for idx, label in enumerate(labels):
        digest = hashlib.sha256(f"{segment_id}:{GENRE_MODEL_KEY}:{idx}".encode()).hexdigest()
        score = int(digest[:8], 16) / 0xFFFFFFFF
        scored.append((label, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [{"label": label, "score": score} for label, score in scored[:k]]


@dataclass(frozen=True)
class GenreRunResult:
    genre_outputs: dict[str, dict[str, Any]]
    models_missing: list[str]
    inference_mode: str


class GenreRunner:
    """Genre Discogs519 inference on top of MAEST embeddings (phase 6.8B)."""

    def __init__(
        self,
        *,
        model_manager: ModelManager | None = None,
        backend: TensorflowInferenceBackend | None = None,
    ) -> None:
        self._mm = model_manager or ModelManager()
        self._backend = backend

    def run_for_segment(self, *, segment_id: int, wav_path: str) -> GenreRunResult:
        outputs: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        real_used = False
        stub_used = False
        k = max(1, settings.advanced_features_top_k_genres)

        available = self._mm.is_available(GENRE_EXTRACTOR_KEY) and self._mm.is_available(
            GENRE_HEAD_KEY
        )
        if not available:
            missing.append(GENRE_MODEL_KEY)
        elif self._backend is not None:
            activations = self._backend.classifier_activations(
                wav_path, extractor_key=GENRE_EXTRACTOR_KEY, head_key=GENRE_HEAD_KEY
            )
            ranked = sorted(activations, key=lambda pair: pair[1], reverse=True)[:k]
            model_name, model_version = model_identity(self._mm, GENRE_HEAD_KEY)
            outputs[GENRE_MODEL_KEY] = {
                "model_key": GENRE_MODEL_KEY,
                "model_status": "available",
                "top_k": [{"label": label, "score": float(score)} for label, score in ranked],
                "model_name": model_name,
                "model_version": model_version,
                "inference_mode": "real",
                "wav_path_used": True,
            }
            real_used = True
        elif stubs_allowed():
            model_name, model_version = model_identity(self._mm, GENRE_HEAD_KEY)
            outputs[GENRE_MODEL_KEY] = {
                "model_key": GENRE_MODEL_KEY,
                "model_status": "available",
                "top_k": _deterministic_top_k(segment_id, k=k),
                "model_name": model_name,
                "model_version": model_version,
                "inference_mode": "stub",
            }
            stub_used = True
        else:
            ensure_stub_allowed(model_key=GENRE_MODEL_KEY)

        return GenreRunResult(
            genre_outputs=outputs,
            models_missing=missing,
            inference_mode=_resolve_mode(real_used, stub_used),
        )


def _resolve_mode(real_used: bool, stub_used: bool) -> str:
    if real_used:
        return "real"
    if stub_used:
        return "stub"
    return "none"
