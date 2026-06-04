from __future__ import annotations

from typing import Any

# Error codes raised by the Essentia TensorFlow inference layer (phase 6.8B).
STUB_INFERENCE_FORBIDDEN = "STUB_INFERENCE_FORBIDDEN"
TENSORFLOW_INFERENCE_FAILED = "TENSORFLOW_INFERENCE_FAILED"
MODEL_MISSING = "MODEL_MISSING"
MODEL_INVALID = "MODEL_INVALID"


class InferenceError(Exception):
    """Domain error raised during real/stub TensorFlow inference.

    The worker maps ``code`` to ``mark_failed(error_code=...)`` so the job
    item carries a stable, documented error code.
    """

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
