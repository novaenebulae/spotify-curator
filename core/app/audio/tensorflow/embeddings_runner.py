from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.models_registry import ModelRegistry
from app.models_registry.definitions import MODEL_DEFINITIONS
from app.models_registry.types import ModelStatus

EFFNET_MODEL_KEY = "discogs_effnet_embeddings"


def _definition_dimension(model_key: str) -> int:
    for d in MODEL_DEFINITIONS:
        if d.model_key == model_key and d.dimension is not None:
            return d.dimension
    return 1280


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
    """Stub embedding inference (phase 6.6) until real Essentia TF is wired."""

    def __init__(self, *, registry: ModelRegistry | None = None) -> None:
        self._registry = registry or ModelRegistry()

    def run_for_segment(self, *, segment_id: int, wav_path: str) -> EmbeddingsRunResult:
        del wav_path
        statuses, _ = self._registry.scan()
        by_key = {s.model_key: s for s in statuses}
        outputs: dict[str, dict[str, Any]] = {}
        missing: list[str] = []

        status = by_key.get(EFFNET_MODEL_KEY)
        if status is None or status.status != "available":
            missing.append(EFFNET_MODEL_KEY)
        else:
            dim = status.dimension or _definition_dimension(EFFNET_MODEL_KEY)
            outputs[EFFNET_MODEL_KEY] = {
                "model_key": EFFNET_MODEL_KEY,
                "model_status": "available",
                "dimension": dim,
                "vector": _deterministic_vector(segment_id, EFFNET_MODEL_KEY, dim),
                "model_name": status.model_name,
                "model_version": status.version,
            }

        return EmbeddingsRunResult(
            embedding_outputs=outputs,
            models_missing=missing,
            inference_mode="stub",
        )
