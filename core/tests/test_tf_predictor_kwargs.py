from __future__ import annotations

from app.audio.tensorflow.backend import build_predictor_kwargs


def test_build_predictor_kwargs_2d_uses_singular_io() -> None:
    kwargs = build_predictor_kwargs(
        "TensorflowPredict2D",
        graph="/models/head.pb",
        output="model/Identity",
        input_node="model/Placeholder",
    )
    assert kwargs == {
        "graphFilename": "/models/head.pb",
        "output": "model/Identity",
        "input": "model/Placeholder",
    }


def test_build_predictor_kwargs_maest_uses_io_lists() -> None:
    kwargs = build_predictor_kwargs(
        "TensorflowPredictMAEST",
        graph="/models/maest.pb",
        output="PartitionedCall/Identity_13",
    )
    assert kwargs == {
        "graphFilename": "/models/maest.pb",
        "outputs": ["PartitionedCall/Identity_13"],
    }


def test_build_predictor_kwargs_effnet_uses_io_lists() -> None:
    kwargs = build_predictor_kwargs(
        "TensorflowPredictEffnetDiscogs",
        graph="/models/effnet.pb",
        output="PartitionedCall:1",
        input_node="serving_default_model_Placeholder",
    )
    assert kwargs == {
        "graphFilename": "/models/effnet.pb",
        "outputs": ["PartitionedCall:1"],
        "inputs": ["serving_default_model_Placeholder"],
    }
