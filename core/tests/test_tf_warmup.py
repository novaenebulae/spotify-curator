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


def test_warmup_maest_genre_classifier_uses_extractor_graph() -> None:
    mm = MagicMock()
    mm.resolve_profile.return_value = ["genre_discogs519_maest_519l"]
    mm.is_available.return_value = True
    mm.get_entry.return_value = MagicMock(
        task="genre_classifier",
        output=None,
        depends_on=["discogs_maest_30s_pw_519l"],
        sample_rate=16000,
    )
    mm.read_metadata.side_effect = lambda key: (
        {
            "schema": {
                "outputs": [
                    {"name": "PartitionedCall/Identity_13", "output_purpose": "predictions"},
                ]
            }
        }
        if key == "discogs_maest_30s_pw_519l"
        else {}
    )
    mm.weights_path.side_effect = lambda key: f"/models/{key}.pb"

    backend = MagicMock(spec=EssentiaTensorflowBackend)
    backend._predictor_cache = {}
    backend._get_predictor = MagicMock()

    def _run():
        return warmup_tensorflow_predictors(
            model_manager=mm, backend=backend, profile="phase6-recommended"
        )

    result = _with_essentia_mock(_run)

    assert result["loaded_predictors"] == ["genre_discogs519_maest_519l"]
    backend._get_predictor.assert_called_once()
    call = backend._get_predictor.call_args
    assert call.args[1] == "TensorflowPredictMAEST"
    assert call.kwargs["graph"] == "/models/discogs_maest_30s_pw_519l.pb"
    assert call.kwargs["output"] == "PartitionedCall/Identity_13"


def test_warmup_optional_head_failure_does_not_raise() -> None:
    mm = MagicMock()
    mm.resolve_profile.return_value = ["discogs_effnet_bs64", "mood_happy_discogs_effnet"]
    mm.is_available.return_value = True
    mm.get_entry.side_effect = lambda key: MagicMock(
        task="embedding" if key == "discogs_effnet_bs64" else "classifier",
        output="out",
        depends_on=() if key == "discogs_effnet_bs64" else ["discogs_effnet_bs64"],
        sample_rate=16000,
    )
    mm.read_metadata.return_value = {}
    mm.weights_path.side_effect = lambda key: f"/models/{key}.pb"

    backend = MagicMock(spec=EssentiaTensorflowBackend)
    backend._predictor_cache = {}

    def _get_predictor(*_args, **_kwargs):
        if _kwargs.get("graph") == "/models/mood_happy_discogs_effnet.pb":
            raise RuntimeError("head warmup failed")
        return MagicMock()

    backend._get_predictor = MagicMock(side_effect=_get_predictor)

    def _run():
        return warmup_tensorflow_predictors(
            model_manager=mm, backend=backend, profile="phase6-recommended"
        )

    result = _with_essentia_mock(_run)

    assert "discogs_effnet_bs64" in result["loaded_predictors"]
    assert "mood_happy_discogs_effnet" in result["warmup_failed_optional"]
