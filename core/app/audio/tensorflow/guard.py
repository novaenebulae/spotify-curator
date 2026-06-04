from __future__ import annotations

from app.audio.tensorflow.errors import STUB_INFERENCE_FORBIDDEN, InferenceError
from app.settings.config import settings


def stubs_allowed() -> bool:
    """Stub inference is only tolerated inside the test environment.

    Both conditions are required (see docs/07 and docs/14):
    - ``APP_ENV=test``
    - ``ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=true``
    """
    return settings.app_env == "test" and settings.essentia_tf_allow_stubs_in_tests


def ensure_stub_allowed(*, model_key: str | None = None) -> None:
    """Raise unless stub inference is explicitly allowed in tests."""
    if stubs_allowed():
        return
    details: dict[str, str] = {}
    if model_key is not None:
        details["model_key"] = model_key
    raise InferenceError(
        code=STUB_INFERENCE_FORBIDDEN,
        message=(
            "Stub TensorFlow inference is forbidden outside the test environment "
            "(set APP_ENV=test and ESSENTIA_TF_ALLOW_STUBS_IN_TESTS=true to allow)."
        ),
        details=details,
    )
