from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.features.embeddings.genre_discogs import stub_label_pool
from app.models_registry import ModelRegistry
from app.settings.config import settings

GENRE_MODEL_KEY = "genre_discogs_519"


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
    """Stub genre Discogs519 inference (phase 6.6)."""

    def __init__(self, *, registry: ModelRegistry | None = None) -> None:
        self._registry = registry or ModelRegistry()

    def run_for_segment(self, *, segment_id: int, wav_path: str) -> GenreRunResult:
        del wav_path
        statuses, _ = self._registry.scan()
        by_key = {s.model_key: s for s in statuses}
        outputs: dict[str, dict[str, Any]] = {}
        missing: list[str] = []

        status = by_key.get(GENRE_MODEL_KEY)
        if status is None or status.status != "available":
            missing.append(GENRE_MODEL_KEY)
        else:
            k = max(1, settings.advanced_features_top_k_genres)
            outputs[GENRE_MODEL_KEY] = {
                "model_key": GENRE_MODEL_KEY,
                "model_status": "available",
                "top_k": _deterministic_top_k(segment_id, k=k),
                "model_name": status.model_name,
                "model_version": status.version,
            }

        return GenreRunResult(
            genre_outputs=outputs,
            models_missing=missing,
            inference_mode="stub",
        )
