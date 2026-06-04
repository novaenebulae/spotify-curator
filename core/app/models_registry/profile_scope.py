from __future__ import annotations

from app.models_registry.manager import ModelManager
from app.settings.config import settings


def model_keys_for_default_profile() -> frozenset[str]:
    """Model keys required by the configured Essentia TensorFlow profile."""
    try:
        return frozenset(ModelManager().resolve_profile(settings.essentia_models_default_profile))
    except Exception:
        return frozenset()


def model_key_in_default_profile(model_key: str) -> bool:
    keys = model_keys_for_default_profile()
    if not keys:
        return True
    return model_key in keys
