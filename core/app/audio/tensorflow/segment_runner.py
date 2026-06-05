from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.audio.tensorflow.backend import EssentiaTensorflowBackend, TensorflowInferenceBackend
from app.audio.tensorflow.classifier_runner import ClassifierRunner
from app.audio.tensorflow.embeddings_runner import EmbeddingsRunner
from app.audio.tensorflow.errors import InferenceError
from app.audio.tensorflow.genre_runner import GENRE_MODEL_KEY, GenreRunner
from app.audio.wav_pad import MAEST_MIN_SECONDS, ensure_min_wav_duration, wav_duration_seconds
from app.models_registry.manager import ModelManager, ModelManagerError


@dataclass(frozen=True)
class SegmentTensorflowResult:
    segment_id: int
    embedding_outputs: dict[str, dict[str, Any]]
    genre_outputs: dict[str, dict[str, Any]]
    classifier_outputs: dict[str, dict[str, Any]]
    models_missing: list[str]
    inference_mode: str


class SegmentTensorflowRunner:
    """Single-pass TensorFlow inference per segment (EffNet + MAEST + classifiers)."""

    def __init__(
        self,
        *,
        model_manager: ModelManager | None = None,
        backend: TensorflowInferenceBackend | None = None,
        embeddings_runner: EmbeddingsRunner | None = None,
        genre_runner: GenreRunner | None = None,
        classifier_runner: ClassifierRunner | None = None,
    ) -> None:
        self._mm = model_manager or ModelManager()
        self._backend = backend
        self._embeddings = embeddings_runner
        self._genre = genre_runner
        self._classifier = classifier_runner

    def run_for_segment(self, *, segment_id: int, wav_path: str) -> SegmentTensorflowResult:
        self._ensure_maest_duration(Path(wav_path))

        backend: TensorflowInferenceBackend = (
            self._backend or EssentiaTensorflowBackend(model_manager=self._mm)
        )
        emb_runner = self._embeddings or EmbeddingsRunner(
            model_manager=self._mm, backend=backend
        )
        genre_runner = self._genre or GenreRunner(
            model_manager=self._mm, backend=backend
        )
        clf_runner = self._classifier or ClassifierRunner(
            model_manager=self._mm, backend=backend
        )

        emb = emb_runner.run_for_segment(segment_id=segment_id, wav_path=wav_path)
        genre_outputs: dict[str, dict[str, Any]] = {}
        genre_missing: list[str] = []
        genre_mode = "none"
        try:
            genre = genre_runner.run_for_segment(segment_id=segment_id, wav_path=wav_path)
            genre_outputs = genre.genre_outputs
            genre_missing = list(genre.models_missing)
            genre_mode = genre.inference_mode
        except (InferenceError, ModelManagerError) as genre_exc:
            if _is_audio_too_short(genre_exc):
                genre_outputs = {
                    GENRE_MODEL_KEY: {
                        "model_key": GENRE_MODEL_KEY,
                        "model_status": "missing",
                        "error_code": "AUDIO_TOO_SHORT",
                        "error_message": str(genre_exc),
                        "top_k": [],
                    }
                }
            else:
                raise

        clf = clf_runner.run_for_segment(segment_id=segment_id, wav_path=wav_path)

        models_missing = sorted(
            set(emb.models_missing) | set(genre_missing) | set(clf.models_missing)
        )
        go = genre_outputs.get(GENRE_MODEL_KEY) if isinstance(genre_outputs, dict) else None
        if isinstance(go, dict) and go.get("top_k"):
            models_missing = [m for m in models_missing if m != GENRE_MODEL_KEY]

        inference = _resolve_inference_mode(emb.inference_mode, genre_mode, clf.inference_mode)

        return SegmentTensorflowResult(
            segment_id=segment_id,
            embedding_outputs=emb.embedding_outputs,
            genre_outputs=genre_outputs,
            classifier_outputs=clf.classifier_outputs,
            models_missing=models_missing,
            inference_mode=inference,
        )

    @staticmethod
    def _ensure_maest_duration(wav: Path) -> None:
        try:
            if wav_duration_seconds(wav) < MAEST_MIN_SECONDS:
                ensure_min_wav_duration(wav)
        except Exception:  # noqa: BLE001
            pass

    def to_result_json(
        self, result: SegmentTensorflowResult, *, stage_name: str
    ) -> dict[str, Any]:
        return {
            "segment_id": result.segment_id,
            "stage_name": stage_name,
            "status_only": False,
            "inference": result.inference_mode,
            "embedding_outputs": result.embedding_outputs,
            "genre_outputs": result.genre_outputs,
            "classifier_outputs": result.classifier_outputs,
            "models_missing": result.models_missing,
        }


def _is_audio_too_short(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "too short" in msg or "signal is too short" in msg


def _resolve_inference_mode(*modes: str) -> str:
    if any(m == "real" for m in modes):
        return "real"
    if any(m == "stub" for m in modes):
        return "stub"
    return "none"
