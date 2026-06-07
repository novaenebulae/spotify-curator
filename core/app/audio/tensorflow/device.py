from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.settings.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TensorflowDeviceInfo:
    tensorflow_version: str | None
    gpu_available: bool
    gpu_devices: list[str]
    device_mode: str


def _import_tensorflow():
    import tensorflow as tf  # type: ignore[import-not-found]

    return tf


def configure_tensorflow_device() -> TensorflowDeviceInfo:
    """Apply GPU/CPU preferences and return runtime device diagnostics."""
    mode = (settings.essentia_tf_device or "auto").strip().lower()
    tf_version: str | None = None
    gpu_names: list[str] = []

    try:
        tf = _import_tensorflow()
        tf_version = str(tf.__version__)
    except Exception as exc:  # noqa: BLE001
        logger.warning("TensorFlow import failed during device setup: %s", exc)
        return TensorflowDeviceInfo(
            tensorflow_version=None,
            gpu_available=False,
            gpu_devices=[],
            device_mode=mode,
        )

    gpus = tf.config.list_physical_devices("GPU")
    gpu_names = [str(g.name) for g in gpus]

    if mode == "gpu":
        if not gpus:
            logger.error(
                "ESSENTIA_TF_DEVICE=gpu but TensorFlow sees no GPU devices",
                extra={"device_mode": mode},
            )
        for gpu in gpus:
            try:
                tf.config.experimental.set_memory_growth(gpu, True)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not enable GPU memory growth for %s: %s", gpu, exc)
    elif mode == "cpu":
        try:
            tf.config.set_visible_devices([], "GPU")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not hide GPU devices for CPU mode: %s", exc)

    return TensorflowDeviceInfo(
        tensorflow_version=tf_version,
        gpu_available=bool(gpus),
        gpu_devices=gpu_names,
        device_mode=mode,
    )


def device_info_to_dict(info: TensorflowDeviceInfo) -> dict[str, Any]:
    return {
        "tensorflow_version": info.tensorflow_version,
        "gpu_available": info.gpu_available,
        "gpu_devices": info.gpu_devices,
        "device_mode": info.device_mode,
    }
