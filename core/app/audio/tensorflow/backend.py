from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.audio.tensorflow.errors import TENSORFLOW_INFERENCE_FAILED, InferenceError
from app.models_registry.manager import ModelManager

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_EMBEDDING_DIM = 1280


@runtime_checkable
class TensorflowInferenceBackend(Protocol):
    """Abstraction over real Essentia TensorFlow inference.

    Production uses :class:`EssentiaTensorflowBackend` (lazy ``essentia`` import,
    only available inside the Docker ``essentia-tensorflow-worker`` image). Tests
    inject a deterministic fake derived from the WAV bytes so results change when
    the audio changes, without importing Essentia.
    """

    def embeddings(self, wav_path: str, *, extractor_key: str) -> list[float]:
        """Return a single embedding vector for the segment (frames averaged)."""
        ...

    def classifier_activations(
        self, wav_path: str, *, extractor_key: str, head_key: str
    ) -> list[tuple[str, float]]:
        """Return ``(label, score)`` pairs from a classification/genre head."""
        ...


class EssentiaTensorflowBackend:
    """Real inference backend. Imports ``essentia`` lazily at call time."""

    def __init__(self, *, model_manager: ModelManager) -> None:
        self._mm = model_manager

    def embeddings(self, wav_path: str, *, extractor_key: str) -> list[float]:
        try:
            vector = self._extractor_embeddings(wav_path, extractor_key)
        except InferenceError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize to domain error
            raise InferenceError(
                code=TENSORFLOW_INFERENCE_FAILED,
                message=f"Embeddings inference failed for {extractor_key}: {exc}",
                details={"model_key": extractor_key},
            ) from exc
        return vector

    def classifier_activations(
        self, wav_path: str, *, extractor_key: str, head_key: str
    ) -> list[tuple[str, float]]:
        try:
            return self._head_activations(wav_path, extractor_key, head_key)
        except InferenceError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize to domain error
            raise InferenceError(
                code=TENSORFLOW_INFERENCE_FAILED,
                message=f"Head inference failed for {head_key}: {exc}",
                details={"model_key": head_key, "extractor_key": extractor_key},
            ) from exc

    # ----- internal Essentia helpers ---------------------------------------

    def _load_audio(self, wav_path: str, sample_rate: int):
        import essentia.standard as es  # type: ignore[import-not-found]

        loader = es.MonoLoader(filename=wav_path, sampleRate=sample_rate, resampleQuality=4)
        return loader()

    def _embedding_frames(self, wav_path: str, extractor_key: str):
        import essentia.standard as es  # type: ignore[import-not-found]

        entry = self._mm.get_entry(extractor_key)
        meta = self._mm.read_metadata(extractor_key) or {}
        graph = str(self._mm.weights_path(extractor_key))
        sample_rate = int(entry.sample_rate or _meta_sample_rate(meta) or DEFAULT_SAMPLE_RATE)
        output = entry.output or _meta_output(meta, purpose="embeddings")
        algo_name = _meta_algorithm(meta) or _default_extractor_algorithm(extractor_key)

        audio = self._load_audio(wav_path, sample_rate)
        algo_cls = getattr(es, algo_name)
        kwargs: dict[str, object] = {"graphFilename": graph}
        if output:
            kwargs["output"] = output
        predictor = algo_cls(**kwargs)
        return predictor(audio)

    def _extractor_embeddings(self, wav_path: str, extractor_key: str) -> list[float]:
        frames = self._embedding_frames(wav_path, extractor_key)
        return _mean_rows(frames)

    def _head_activations(
        self, wav_path: str, extractor_key: str, head_key: str
    ) -> list[tuple[str, float]]:
        import essentia.standard as es  # type: ignore[import-not-found]

        embeddings = self._embedding_frames(wav_path, extractor_key)
        head_meta = self._mm.read_metadata(head_key) or {}
        head_entry = self._mm.get_entry(head_key)
        graph = str(self._mm.weights_path(head_key))
        output = (
            head_entry.output
            or _meta_output(head_meta, purpose="predictions")
            or "PartitionedCall"
        )
        predictor = es.TensorflowPredict2D(
            graphFilename=graph,
            input="serving_default_model_Placeholder",
            output=output,
        )
        activations = predictor(embeddings)
        scores = _mean_rows(activations)
        labels = _meta_classes(head_meta) or [f"class_{i}" for i in range(len(scores))]
        return [(str(labels[i]), float(scores[i])) for i in range(min(len(labels), len(scores)))]


# ----- metadata helpers -----------------------------------------------------


def _meta_sample_rate(meta: dict) -> int | None:
    inference = meta.get("inference") if isinstance(meta, dict) else None
    if isinstance(inference, dict):
        value = inference.get("sample_rate")
        if isinstance(value, (int, float)):
            return int(value)
    return None


def _meta_algorithm(meta: dict) -> str | None:
    inference = meta.get("inference") if isinstance(meta, dict) else None
    if isinstance(inference, dict):
        algo = inference.get("algorithm")
        if isinstance(algo, str) and algo:
            return algo
    return None


def _meta_output(meta: dict, *, purpose: str) -> str | None:
    schema = meta.get("schema") if isinstance(meta, dict) else None
    if not isinstance(schema, dict):
        return None
    outputs = schema.get("outputs")
    if not isinstance(outputs, list):
        return None
    for out in outputs:
        if isinstance(out, dict) and out.get("output_purpose") == purpose:
            name = out.get("name")
            if isinstance(name, str) and name:
                return name
    for out in outputs:
        if isinstance(out, dict):
            name = out.get("name")
            if isinstance(name, str) and name:
                return name
    return None


def _meta_classes(meta: dict) -> list[str]:
    classes = meta.get("classes") if isinstance(meta, dict) else None
    if isinstance(classes, list):
        return [str(c) for c in classes]
    return []


def model_identity(model_manager: ModelManager, model_key: str) -> tuple[str, str | None]:
    """Return ``(model_name, model_version)`` from metadata or the manifest entry."""
    meta = model_manager.read_metadata(model_key) or {}
    entry = model_manager.get_entry(model_key)
    name = meta.get("name") if isinstance(meta, dict) else None
    version = meta.get("version") if isinstance(meta, dict) else None
    model_name = str(name) if name else entry.display_name
    model_version = str(version) if version is not None else None
    return model_name, model_version


def _default_extractor_algorithm(extractor_key: str) -> str:
    key = extractor_key.lower()
    if "maest" in key:
        return "TensorflowPredictMAEST"
    if "musicnn" in key:
        return "TensorflowPredictMusiCNN"
    return "TensorflowPredictEffnetDiscogs"


def _mean_rows(matrix) -> list[float]:
    """Average a 2D activation/embedding matrix over its frame axis."""
    rows = list(matrix)
    if not rows:
        return []
    first = rows[0]
    try:
        width = len(first)
    except TypeError:
        # 1D vector already.
        return [float(v) for v in rows]
    sums = [0.0] * width
    count = 0
    for row in rows:
        count += 1
        for i in range(width):
            sums[i] += float(row[i])
    if count == 0:
        return [0.0] * width
    return [s / count for s in sums]
