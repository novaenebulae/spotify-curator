from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.audio.tensorflow.errors import TENSORFLOW_INFERENCE_FAILED, InferenceError
from app.audio.tensorflow.model_map import EMBEDDINGS_EXTRACTOR_KEY
from app.models_registry.manager import ModelManager

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_EMBEDDING_DIM = 1280

# Small LRU bounds: within one segment all heads share the same WAV, so a tiny
# cache collapses the ~12 redundant EffNet inferences into one while keeping
# memory flat across the many segments a persistent worker processes.
_AUDIO_CACHE_SIZE = 2
_FRAMES_CACHE_SIZE = 2


@dataclass
class SegmentTimingMs:
    mono_loader_ms: float = 0.0
    effnet_forward_ms: float = 0.0
    maest_forward_ms: float = 0.0
    classifier_heads_ms: float = 0.0
    total_tensorflow_stage_ms: float = 0.0
    frames_cache_size: int = 0
    predictor_cache_size: int = 0

    def as_dict(self) -> dict[str, float | int]:
        return {
            "mono_loader_ms": round(self.mono_loader_ms, 2),
            "effnet_forward_ms": round(self.effnet_forward_ms, 2),
            "maest_forward_ms": round(self.maest_forward_ms, 2),
            "classifier_heads_ms": round(self.classifier_heads_ms, 2),
            "total_tensorflow_stage_ms": round(self.total_tensorflow_stage_ms, 2),
            "frames_cache_size": self.frames_cache_size,
            "predictor_cache_size": self.predictor_cache_size,
        }


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
        # Predictor graphs are static -> memoize for the worker lifetime
        # (~14 models). Audio/frames are WAV-scoped -> small LRU to bound memory.
        self._predictor_cache: dict[tuple, Any] = {}
        self._audio_cache: OrderedDict[tuple, Any] = OrderedDict()
        self._frames_cache: OrderedDict[tuple, Any] = OrderedDict()
        self._segment_timing = SegmentTimingMs()
        self._segment_started_at: float | None = None

    def begin_segment_timing(self) -> None:
        self._segment_timing = SegmentTimingMs()
        self._segment_started_at = time.perf_counter()

    def consume_segment_timing(self) -> dict[str, float | int]:
        if self._segment_started_at is not None:
            self._segment_timing.total_tensorflow_stage_ms = (
                time.perf_counter() - self._segment_started_at
            ) * 1000
        self._segment_timing.frames_cache_size = len(self._frames_cache)
        self._segment_timing.predictor_cache_size = len(self._predictor_cache)
        return self._segment_timing.as_dict()

    @property
    def predictor_cache_size(self) -> int:
        return len(self._predictor_cache)

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

    def run_effnet_classifier_heads(
        self, wav_path: str, head_keys: list[str]
    ) -> dict[str, list[tuple[str, float]]]:
        """Run multiple EffNet 2D heads after a single embedding-frame extraction."""
        if not head_keys:
            return {}
        try:
            heads_started = time.perf_counter()
            frames = self._embedding_frames(wav_path, EMBEDDINGS_EXTRACTOR_KEY)
            result = {
                head_key: self.head_activations_from_frames(
                    frames, extractor_key=EMBEDDINGS_EXTRACTOR_KEY, head_key=head_key
                )
                for head_key in head_keys
            }
            self._segment_timing.classifier_heads_ms += (
                time.perf_counter() - heads_started
            ) * 1000
            return result
        except InferenceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise InferenceError(
                code=TENSORFLOW_INFERENCE_FAILED,
                message=f"EffNet batch head inference failed: {exc}",
                details={"head_keys": head_keys},
            ) from exc

    def head_activations_from_frames(
        self, frames, *, extractor_key: str, head_key: str
    ) -> list[tuple[str, float]]:
        """Run a 2D head on precomputed extractor frames (no WAV reload)."""
        import essentia.standard as es  # type: ignore[import-not-found]

        head_meta = self._mm.read_metadata(head_key) or {}
        ext_meta = self._mm.read_metadata(extractor_key) or {}
        if _use_direct_extractor_predictions(extractor_key, head_key, ext_meta):
            raise InferenceError(
                code=TENSORFLOW_INFERENCE_FAILED,
                message="head_activations_from_frames requires 2D heads, not MAEST direct",
                details={"head_key": head_key},
            )
        head_entry = self._mm.get_entry(head_key)
        graph = str(self._mm.weights_path(head_key))
        input_node = _meta_input(head_meta) or "model/Placeholder"
        output = (
            head_entry.output or _meta_output(head_meta, purpose="predictions") or "model/Identity"
        )
        predictor = self._get_predictor(
            es,
            "TensorflowPredict2D",
            graph=graph,
            output=output,
            input_node=input_node,
        )
        activations = predictor(frames)
        scores = _mean_rows(activations)
        labels = _meta_classes(head_meta) or [f"class_{i}" for i in range(len(scores))]
        return [(str(labels[i]), float(scores[i])) for i in range(min(len(labels), len(scores)))]

    # ----- internal Essentia helpers ---------------------------------------

    def _load_audio(self, wav_path: str, sample_rate: int):
        key = (wav_path, sample_rate)
        cached = self._audio_cache.get(key)
        if cached is not None:
            self._audio_cache.move_to_end(key)
            return cached

        import essentia.standard as es  # type: ignore[import-not-found]

        # MonoLoader must receive ``filename`` at construction time. Reusing an
        # instance and calling ``configure(filename=...)`` skips resampling to
        # ``sampleRate`` for 44.1 kHz Deezer previews (~82 s at 16 kHz).
        load_started = time.perf_counter()
        loader = es.MonoLoader(
            sampleRate=sample_rate,
            resampleQuality=4,
            filename=wav_path,
        )
        audio = loader()
        self._segment_timing.mono_loader_ms += (time.perf_counter() - load_started) * 1000
        self._audio_cache[key] = audio
        self._audio_cache.move_to_end(key)
        while len(self._audio_cache) > _AUDIO_CACHE_SIZE:
            self._audio_cache.popitem(last=False)
        return audio

    def _get_predictor(
        self,
        es,
        algo_name: str,
        *,
        graph: str,
        output: str | None = None,
        input_node: str | None = None,
    ):
        """Build (and memoize) an Essentia predictor keyed by its graph + I/O nodes."""
        key = (algo_name, graph, output, input_node)
        cached = self._predictor_cache.get(key)
        if cached is not None:
            return cached
        algo_cls = getattr(es, algo_name)
        kwargs = build_predictor_kwargs(
            algo_name, graph=graph, output=output, input_node=input_node
        )
        predictor = algo_cls(**kwargs)
        self._predictor_cache[key] = predictor
        return predictor

    def _embedding_frames(self, wav_path: str, extractor_key: str):
        key = (wav_path, extractor_key)
        cached = self._frames_cache.get(key)
        if cached is not None:
            self._frames_cache.move_to_end(key)
            return cached

        import essentia.standard as es  # type: ignore[import-not-found]

        entry = self._mm.get_entry(extractor_key)
        meta = self._mm.read_metadata(extractor_key) or {}
        graph = str(self._mm.weights_path(extractor_key))
        sample_rate = int(entry.sample_rate or _meta_sample_rate(meta) or DEFAULT_SAMPLE_RATE)
        output = entry.output or _meta_output(meta, purpose="embeddings")
        algo_name = _meta_algorithm(meta) or _default_extractor_algorithm(extractor_key)

        audio = self._load_audio(wav_path, sample_rate)
        predictor = self._get_predictor(es, algo_name, graph=graph, output=output)
        forward_started = time.perf_counter()
        frames = predictor(audio)
        elapsed_ms = (time.perf_counter() - forward_started) * 1000
        if "maest" in extractor_key.lower():
            self._segment_timing.maest_forward_ms += elapsed_ms
        else:
            self._segment_timing.effnet_forward_ms += elapsed_ms
        self._frames_cache[key] = frames
        self._frames_cache.move_to_end(key)
        while len(self._frames_cache) > _FRAMES_CACHE_SIZE:
            self._frames_cache.popitem(last=False)
        return frames

    def _extractor_embeddings(self, wav_path: str, extractor_key: str) -> list[float]:
        frames = self._embedding_frames(wav_path, extractor_key)
        return _mean_rows(frames)

    def _head_activations(
        self, wav_path: str, extractor_key: str, head_key: str
    ) -> list[tuple[str, float]]:
        import essentia.standard as es  # type: ignore[import-not-found]

        head_meta = self._mm.read_metadata(head_key) or {}
        ext_meta = self._mm.read_metadata(extractor_key) or {}

        # MAEST (and same-key models) expose ``predictions`` on the extractor graph.
        # EffNet also has a 400-class ``predictions`` output, but mood/danceability
        # heads must run TensorflowPredict2D on embeddings (PartitionedCall:1).
        if _use_direct_extractor_predictions(extractor_key, head_key, ext_meta):
            return self._direct_predictions(
                wav_path, extractor_key, fallback_classes=_meta_classes(head_meta)
            )

        frames = self._embedding_frames(wav_path, extractor_key)
        return self.head_activations_from_frames(
            frames, extractor_key=extractor_key, head_key=head_key
        )

    def _direct_predictions(
        self, wav_path: str, extractor_key: str, *, fallback_classes: list[str]
    ) -> list[tuple[str, float]]:
        """Single-stage inference for self-classifying extractors (e.g. MAEST)."""
        import essentia.standard as es  # type: ignore[import-not-found]

        entry = self._mm.get_entry(extractor_key)
        meta = self._mm.read_metadata(extractor_key) or {}
        graph = str(self._mm.weights_path(extractor_key))
        sample_rate = int(entry.sample_rate or _meta_sample_rate(meta) or DEFAULT_SAMPLE_RATE)
        output = _predictions_output(meta)
        algo_name = _meta_algorithm(meta) or _default_extractor_algorithm(extractor_key)

        audio = self._load_audio(wav_path, sample_rate)
        predictor = self._get_predictor(es, algo_name, graph=graph, output=output)
        forward_started = time.perf_counter()
        scores = _reduce_predictions(predictor(audio))
        self._segment_timing.maest_forward_ms += (time.perf_counter() - forward_started) * 1000
        labels = (
            _meta_classes(meta) or fallback_classes or [f"class_{i}" for i in range(len(scores))]
        )
        return [(str(labels[i]), float(scores[i])) for i in range(min(len(labels), len(scores)))]


# ----- predictor construction -----------------------------------------------


def build_predictor_kwargs(
    algo_name: str,
    *,
    graph: str,
    output: str | None = None,
    input_node: str | None = None,
) -> dict[str, object]:
    """Map Essentia algorithm families to correct graph I/O parameter names.

    TensorflowPredict2D uses ``input`` / ``output``.
    TensorflowPredict* (EffNet, MAEST, MusiCNN, …) use ``inputs`` / ``outputs`` lists.
    """
    kwargs: dict[str, object] = {"graphFilename": graph}
    if algo_name == "TensorflowPredict2D":
        if output:
            kwargs["output"] = output
        if input_node:
            kwargs["input"] = input_node
        return kwargs
    if algo_name.startswith("TensorflowPredict"):
        if output:
            kwargs["outputs"] = [output]
        if input_node:
            kwargs["inputs"] = [input_node]
        return kwargs
    if output:
        kwargs["output"] = output
    if input_node:
        kwargs["input"] = input_node
    return kwargs


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


def _use_direct_extractor_predictions(
    extractor_key: str, head_key: str, ext_meta: dict
) -> bool:
    """True only for self-contained extractors (MAEST), not EffNet + separate head."""
    if _predictions_output(ext_meta) is None:
        return False
    if extractor_key == head_key:
        return True
    return "maest" in extractor_key.lower()


def _predictions_output(meta: dict) -> str | None:
    """Return the node name of a ``predictions`` output, if the model has one."""
    schema = meta.get("schema") if isinstance(meta, dict) else None
    if not isinstance(schema, dict):
        return None
    outputs = schema.get("outputs")
    if not isinstance(outputs, list):
        return None
    for out in outputs:
        if isinstance(out, dict) and out.get("output_purpose") == "predictions":
            name = out.get("name")
            if isinstance(name, str) and name:
                return name
    return None


def _meta_input(meta: dict) -> str | None:
    schema = meta.get("schema") if isinstance(meta, dict) else None
    if not isinstance(schema, dict):
        return None
    inputs = schema.get("inputs")
    if not isinstance(inputs, list):
        return None
    for inp in inputs:
        if isinstance(inp, dict):
            name = inp.get("name")
            if isinstance(name, str) and name:
                return name
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


def _reduce_predictions(activations) -> list[float]:
    """Average a (possibly rank-3) prediction array over all but the class axis.

    MAEST emits predictions shaped like ``[patches, 1, n_classes]``; collapse the
    leading axes so we get one score per class.
    """
    import numpy as np  # type: ignore[import-not-found]

    arr = np.asarray(activations, dtype=float)
    if arr.ndim == 0:
        return [float(arr)]
    arr = arr.reshape(-1, arr.shape[-1])
    return [float(v) for v in arr.mean(axis=0)]


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
