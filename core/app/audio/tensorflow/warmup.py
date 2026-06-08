from __future__ import annotations

import logging
import time
from typing import Any

from app.audio.tensorflow.backend import (
    EssentiaTensorflowBackend,
    _use_direct_extractor_predictions,
)
from app.audio.tensorflow.errors import MODEL_MISSING, InferenceError
from app.audio.tensorflow.model_map import (
    EMBEDDINGS_EXTRACTOR_KEY,
    GENRE_EXTRACTOR_KEY,
)
from app.models_registry.manager import ModelManager
from app.settings.config import settings

logger = logging.getLogger(__name__)

_WARMUP_CRITICAL_KEYS = frozenset({EMBEDDINGS_EXTRACTOR_KEY, GENRE_EXTRACTOR_KEY})


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


def _is_warmup_critical(model_key: str) -> bool:
    return model_key in _WARMUP_CRITICAL_KEYS


def _warmup_head_model(
    be: EssentiaTensorflowBackend,
    es,
    mm: ModelManager,
    *,
    model_key: str,
    entry,
    meta: dict,
    graph: str,
    task: str,
) -> None:
    ext_key = (entry.depends_on or [EMBEDDINGS_EXTRACTOR_KEY])[0]
    ext_meta = mm.read_metadata(ext_key) or {}
    if _use_direct_extractor_predictions(ext_key, model_key, ext_meta):
        output = _predictions_output(ext_meta) or _meta_output(ext_meta, purpose="predictions")
        algo = _meta_algorithm(ext_meta) or _default_extractor_algorithm(ext_key)
        be._get_predictor(  # noqa: SLF001
            es,
            algo,
            graph=str(mm.weights_path(ext_key)),
            output=output,
        )
        return
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
    disk_missing: list[str] = []
    warmup_failed: list[str] = []

    import essentia.standard as es  # type: ignore[import-not-found]

    for model_key in mm.resolve_profile(active_profile):
        if not mm.is_available(model_key):
            disk_missing.append(model_key)
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
            elif task in ("classifier", "genre_classifier", "regression"):
                _warmup_head_model(
                    be,
                    es,
                    mm,
                    model_key=model_key,
                    entry=entry,
                    meta=meta,
                    graph=graph,
                    task=task,
                )
            else:
                output = entry.output or _meta_output(meta, purpose="predictions")
                algo = _meta_algorithm(meta) or _default_extractor_algorithm(model_key)
                be._get_predictor(es, algo, graph=graph, output=output)  # noqa: SLF001
            loaded.append(model_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Warmup failed for %s: %s", model_key, exc)
            warmup_failed.append(model_key)

    duration_ms = int((time.perf_counter() - started) * 1000)
    optional_warmup_failed = [k for k in warmup_failed if not _is_warmup_critical(k)]
    critical_warmup_failed = [k for k in warmup_failed if _is_warmup_critical(k)]
    critical_disk_missing = [k for k in disk_missing if _is_warmup_critical(k)]

    result = {
        "essentia_model_profile": active_profile,
        "loaded_predictors": loaded,
        "models_missing": disk_missing + warmup_failed,
        "disk_missing": disk_missing,
        "warmup_failed": warmup_failed,
        "warmup_failed_optional": optional_warmup_failed,
        "warmup_duration_ms": duration_ms,
        "predictor_cache_size": len(be._predictor_cache),  # noqa: SLF001
    }

    if critical_disk_missing or critical_warmup_failed:
        raise InferenceError(
            code=MODEL_MISSING,
            message=(
                f"Warmup incomplete for profile {active_profile!r}: "
                f"critical models unavailable "
                f"(disk={critical_disk_missing}, warmup={critical_warmup_failed})"
            ),
            details=result,
        )

    if optional_warmup_failed:
        logger.warning(
            "Warmup skipped optional predictors: %s",
            optional_warmup_failed,
            extra=result,
        )

    return result
