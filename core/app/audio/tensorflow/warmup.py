from __future__ import annotations

import logging
import time
from typing import Any

from app.audio.tensorflow.backend import EssentiaTensorflowBackend
from app.audio.tensorflow.errors import MODEL_MISSING, InferenceError
from app.audio.tensorflow.model_map import EMBEDDINGS_EXTRACTOR_KEY
from app.models_registry.manager import ModelManager
from app.settings.config import settings

logger = logging.getLogger(__name__)


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


def _default_extractor_algorithm(extractor_key: str) -> str:
    key = extractor_key.lower()
    if "maest" in key:
        return "TensorflowPredictMAEST"
    if "musicnn" in key:
        return "TensorflowPredictMusiCNN"
    return "TensorflowPredictEffnetDiscogs"


def _predictions_output(meta: dict) -> str | None:
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


def _use_direct_extractor_predictions(extractor_key: str, head_key: str, ext_meta: dict) -> bool:
    if _predictions_output(ext_meta) is None:
        return False
    if extractor_key == head_key:
        return True
    return "maest" in extractor_key.lower()


def warmup_tensorflow_predictors(
    *,
    model_manager: ModelManager | None = None,
    backend: EssentiaTensorflowBackend | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    """Preload predictor graphs for the active model profile at worker boot."""
    mm = model_manager or ModelManager()
    be = backend or EssentiaTensorflowBackend(model_manager=mm)
    active_profile = profile or settings.effective_essentia_model_profile
    started = time.perf_counter()
    loaded: list[str] = []
    missing: list[str] = []

    import essentia.standard as es  # type: ignore[import-not-found]

    for model_key in mm.resolve_profile(active_profile):
        if not mm.is_available(model_key):
            missing.append(model_key)
            continue
        entry = mm.get_entry(model_key)
        meta = mm.read_metadata(model_key) or {}
        graph = str(mm.weights_path(model_key))
        task = (entry.task or "").lower()

        try:
            if task == "embedding" or model_key == EMBEDDINGS_EXTRACTOR_KEY:
                output = entry.output or _meta_output(meta, purpose="embeddings")
                algo = _meta_algorithm(meta) or _default_extractor_algorithm(model_key)
                be._get_predictor(es, algo, graph=graph, output=output)  # noqa: SLF001
            elif task == "classifier":
                ext_key = (entry.depends_on or [EMBEDDINGS_EXTRACTOR_KEY])[0]
                ext_meta = mm.read_metadata(ext_key) or {}
                if _use_direct_extractor_predictions(ext_key, model_key, ext_meta):
                    output = _predictions_output(ext_meta)
                    algo = _meta_algorithm(ext_meta) or _default_extractor_algorithm(ext_key)
                    be._get_predictor(es, algo, graph=str(mm.weights_path(ext_key)), output=output)  # noqa: SLF001
                else:
                    head_meta = meta
                    input_node = _meta_input(head_meta) or "model/Placeholder"
                    output = (
                        entry.output
                        or _meta_output(head_meta, purpose="predictions")
                        or "model/Identity"
                    )
                    be._get_predictor(  # noqa: SLF001
                        es,
                        "TensorflowPredict2D",
                        graph=graph,
                        output=output,
                        input_node=input_node,
                    )
            else:
                output = entry.output or _meta_output(meta, purpose="predictions")
                algo = _meta_algorithm(meta) or _default_extractor_algorithm(model_key)
                be._get_predictor(es, algo, graph=graph, output=output)  # noqa: SLF001
            loaded.append(model_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Warmup failed for %s: %s", model_key, exc)
            missing.append(model_key)

    duration_ms = int((time.perf_counter() - started) * 1000)
    result = {
        "essentia_model_profile": active_profile,
        "loaded_predictors": loaded,
        "models_missing": missing,
        "warmup_duration_ms": duration_ms,
        "predictor_cache_size": len(be._predictor_cache),  # noqa: SLF001
    }

    if missing:
        raise InferenceError(
            code=MODEL_MISSING,
            message=(
                f"Warmup incomplete for profile {active_profile!r}: "
                f"missing predictors for {missing}"
            ),
            details=result,
        )

    return result
