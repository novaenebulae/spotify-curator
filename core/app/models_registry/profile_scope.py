from __future__ import annotations

import json

from app.models_registry.manager import ModelManager
from app.settings.config import settings


def model_profile_from_job_result(result_json: str | None) -> str:
    """Read ``model_profile`` stored on pipeline job ``result_json``."""
    if not result_json:
        return settings.essentia_models_default_profile
    try:
        payload = json.loads(result_json)
    except json.JSONDecodeError:
        return settings.essentia_models_default_profile
    if isinstance(payload, dict) and payload.get("model_profile"):
        return str(payload["model_profile"])
    return settings.essentia_models_default_profile


def model_keys_for_profile(
    profile: str, *, manager: ModelManager | None = None
) -> frozenset[str]:
    """Resolved manifest model keys for a named profile (includes ``extends``)."""
    mm = manager or ModelManager()
    return frozenset(mm.resolve_profile(profile))


def model_keys_for_default_profile() -> frozenset[str]:
    """Model keys required by the configured Essentia TensorFlow profile."""
    try:
        return model_keys_for_profile(settings.essentia_models_default_profile)
    except Exception:
        return frozenset()


def model_key_in_profile(model_key: str, profile_keys: frozenset[str]) -> bool:
    return model_key in profile_keys


def model_key_in_default_profile(model_key: str) -> bool:
    keys = model_keys_for_default_profile()
    if not keys:
        return True
    return model_key in keys
