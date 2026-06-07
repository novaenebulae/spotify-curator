from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from app.audio.tensorflow.backend import EssentiaTensorflowBackend
from app.audio.tensorflow.errors import MODEL_MISSING, InferenceError
from app.audio.tensorflow.warmup import warmup_tensorflow_predictors


def _with_essentia_mock(fn):
    sys.modules["essentia"] = MagicMock()
    sys.modules["essentia.standard"] = MagicMock()
    try:
        return fn()
    finally:
        sys.modules.pop("essentia", None)
        sys.modules.pop("essentia.standard", None)


def test_warmup_loads_available_predictors() -> None:
    mm = MagicMock()
    mm.resolve_profile.return_value = ["discogs_effnet_bs64"]
    mm.is_available.return_value = True
    mm.get_entry.return_value = MagicMock(
        task="embedding", output="out", depends_on=(), sample_rate=16000
    )
    mm.read_metadata.return_value = {}
    mm.weights_path.return_value = "/models/test.pb"

    backend = MagicMock(spec=EssentiaTensorflowBackend)
    backend._predictor_cache = {}
    backend._get_predictor = MagicMock()

    def _run():
        return warmup_tensorflow_predictors(
            model_manager=mm, backend=backend, profile="phase6-minimal"
        )

    result = _with_essentia_mock(_run)

    assert result["loaded_predictors"] == ["discogs_effnet_bs64"]
    assert result["models_missing"] == []
    backend._get_predictor.assert_called_once()


def test_warmup_fails_when_profile_models_missing() -> None:
    mm = MagicMock()
    mm.resolve_profile.return_value = ["discogs_effnet_bs64"]
    mm.is_available.return_value = False

    backend = MagicMock(spec=EssentiaTensorflowBackend)
    backend._predictor_cache = {}

    def _run():
        warmup_tensorflow_predictors(model_manager=mm, backend=backend, profile="phase6-minimal")

    with pytest.raises(InferenceError) as exc:
        _with_essentia_mock(_run)

    assert exc.value.code == MODEL_MISSING
