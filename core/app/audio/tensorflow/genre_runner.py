from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.audio.tensorflow.backend import TensorflowInferenceBackend, model_identity
from app.audio.tensorflow.errors import InferenceError
from app.audio.tensorflow.guard import ensure_stub_allowed, stubs_allowed
from app.audio.tensorflow.model_map import (
    GENRE_EXTRACTOR_KEY,
    GENRE_HEAD_KEY,
    GENRE_LEGACY_KEY,
)
from app.features.embeddings.genre_discogs import stub_label_pool
from app.models_registry.manager import ModelManager
from app.models_registry.profile_scope import model_key_in_profile, model_keys_for_profile
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

    def run_for_segment(
        self,
        *,
        segment_id: int,
        wav_path: str,
        model_profile: str | None = None,
    ) -> GenreRunResult:
        profile_keys = (
            model_keys_for_profile(model_profile, manager=self._mm)
            if model_profile
            else None
        )
        if profile_keys is not None and not self._genre_in_profile(profile_keys):
            return GenreRunResult(
                genre_outputs={},
                models_missing=[],
                inference_mode="none",
            )

        outputs: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        real_used = False
        stub_used = False
        k = max(1, settings.advanced_features_top_k_genres)

        extractor_ok = self._mm.is_available(GENRE_EXTRACTOR_KEY)
        head_ok = self._mm.is_available(GENRE_HEAD_KEY)
        ext_meta = self._mm.read_metadata(GENRE_EXTRACTOR_KEY) or {}
        from app.audio.tensorflow.backend import _predictions_output

        maest_direct = _predictions_output(ext_meta) is not None
        available = extractor_ok and (head_ok or maest_direct)
        if not available:
            missing.append(GENRE_MODEL_KEY)
            outputs[GENRE_MODEL_KEY] = {
                "model_key": GENRE_MODEL_KEY,
                "model_status": "missing",
                "error_code": "MODEL_NOT_ON_DISK",
                "error_message": (
                    "MAEST extractor missing"
                    if not extractor_ok
                    else "Genre Discogs519 head missing"
                ),
                "top_k": [],
            }
        elif self._backend is not None:
            from pathlib import Path

            from app.audio.wav_pad import (
                MAEST_MIN_SECONDS,
                ensure_min_wav_duration,
                wav_duration_seconds,
            )

            wav_path_obj = Path(wav_path)
            try:
                wav_dur = wav_duration_seconds(wav_path_obj)
            except Exception:  # noqa: BLE001
                wav_dur = 0.0
            if wav_dur < MAEST_MIN_SECONDS:
                try:
                    ensure_min_wav_duration(wav_path_obj)
                except Exception:  # noqa: BLE001
                    pass
            try:
                activations = self._backend.classifier_activations(
                    wav_path, extractor_key=GENRE_EXTRACTOR_KEY, head_key=GENRE_HEAD_KEY
                )
            except (InferenceError, Exception) as exc:  # noqa: BLE001
                if _is_audio_too_short(exc):
                    outputs[GENRE_MODEL_KEY] = {
                        "model_key": GENRE_MODEL_KEY,
                        "model_status": "missing",
                        "error_code": "AUDIO_TOO_SHORT",
                        "error_message": str(exc),
                        "top_k": [],
                    }
                else:
                    raise
            else:
                ranked = sorted(activations, key=lambda pair: pair[1], reverse=True)[:k]
                if not ranked:
                    outputs[GENRE_MODEL_KEY] = {
                        "model_key": GENRE_MODEL_KEY,
                        "model_status": "missing",
                        "error_code": "NO_PREDICTIONS",
                        "error_message": "Genre inference returned no labels",
                        "top_k": [],
                    }
                else:
                    model_name, model_version = model_identity(self._mm, GENRE_HEAD_KEY)
                    outputs[GENRE_MODEL_KEY] = {
                        "model_key": GENRE_MODEL_KEY,
                        "model_status": "available",
                        "top_k": [
                            {"label": label, "score": float(score)} for label, score in ranked
                        ],
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

    @staticmethod
    def _genre_in_profile(profile_keys: frozenset[str]) -> bool:
        return model_key_in_profile(GENRE_EXTRACTOR_KEY, profile_keys) and model_key_in_profile(
            GENRE_HEAD_KEY, profile_keys
        )


def _is_audio_too_short(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "too short" in msg or "signal is too short" in msg


def _resolve_mode(real_used: bool, stub_used: bool) -> str:
    if real_used:
        return "real"
    if stub_used:
        return "stub"
    return "none"
