from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.audio.tensorflow.backend import (
    DEFAULT_EMBEDDING_DIM,
    TensorflowInferenceBackend,
    model_identity,
)
from app.audio.tensorflow.guard import ensure_stub_allowed, stubs_allowed
from app.audio.tensorflow.model_map import (
    EMBEDDINGS_EXTRACTOR_KEY,
    EMBEDDINGS_LEGACY_KEY,
)
from app.models_registry.manager import ModelManager
from app.models_registry.profile_scope import model_key_in_profile, model_keys_for_profile

EFFNET_MODEL_KEY = EMBEDDINGS_LEGACY_KEY


def _deterministic_vector(segment_id: int, model_key: str, dimension: int) -> list[float]:
    out: list[float] = []
    for i in range(dimension):
        digest = hashlib.sha256(f"{segment_id}:{model_key}:{i}".encode()).hexdigest()
        out.append(int(digest[:8], 16) / 0xFFFFFFFF)
    return out


@dataclass(frozen=True)
class EmbeddingsRunResult:
    embedding_outputs: dict[str, dict[str, Any]]
    models_missing: list[str]
    inference_mode: str


class EmbeddingsRunner:
    """Discogs EffNet embedding inference (phase 6.8B).

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

    def run_for_segment(
        self,
        *,
        segment_id: int,
        wav_path: str,
        model_profile: str | None = None,
    ) -> EmbeddingsRunResult:
        outputs: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        real_used = False
        stub_used = False
        profile_keys = (
            model_keys_for_profile(model_profile, manager=self._mm)
            if model_profile
            else None
        )
        if profile_keys is not None and not model_key_in_profile(
            EMBEDDINGS_EXTRACTOR_KEY, profile_keys
        ):
            missing.append(EFFNET_MODEL_KEY)
            return EmbeddingsRunResult(
                embedding_outputs=outputs,
                models_missing=missing,
                inference_mode="none",
            )

        if not self._mm.is_available(EMBEDDINGS_EXTRACTOR_KEY):
            missing.append(EFFNET_MODEL_KEY)
        elif self._backend is not None:
            vector = self._backend.embeddings(wav_path, extractor_key=EMBEDDINGS_EXTRACTOR_KEY)
            if not vector:
                raise ValueError("Embeddings backend returned an empty vector")
            model_name, model_version = model_identity(self._mm, EMBEDDINGS_EXTRACTOR_KEY)
            outputs[EFFNET_MODEL_KEY] = {
                "model_key": EFFNET_MODEL_KEY,
                "model_status": "available",
                "dimension": len(vector),
                "vector": [float(v) for v in vector],
                "model_name": model_name,
                "model_version": model_version,
                "inference_mode": "real",
                "wav_path_used": True,
            }
            real_used = True
        elif stubs_allowed():
            model_name, model_version = model_identity(self._mm, EMBEDDINGS_EXTRACTOR_KEY)
            outputs[EFFNET_MODEL_KEY] = {
                "model_key": EFFNET_MODEL_KEY,
                "model_status": "available",
                "dimension": DEFAULT_EMBEDDING_DIM,
                "vector": _deterministic_vector(
                    segment_id, EFFNET_MODEL_KEY, DEFAULT_EMBEDDING_DIM
                ),
                "model_name": model_name,
                "model_version": model_version,
                "inference_mode": "stub",
            }
            stub_used = True
        else:
            ensure_stub_allowed(model_key=EFFNET_MODEL_KEY)

        return EmbeddingsRunResult(
            embedding_outputs=outputs,
            models_missing=missing,
            inference_mode=_resolve_mode(real_used, stub_used),
        )


def _resolve_mode(real_used: bool, stub_used: bool) -> str:
    if real_used:
        return "real"
    if stub_used:
        return "stub"
    return "none"
