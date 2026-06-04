"""EffNet has both predictions (400 styles) and embeddings outputs; mood heads need 2D."""

from __future__ import annotations

import json
import sys
import types

import pytest

from app.audio.tensorflow.backend import (
    EssentiaTensorflowBackend,
    _use_direct_extractor_predictions,
)
from app.audio.tensorflow.model_map import EMBEDDINGS_EXTRACTOR_KEY

HEAD_MOOD = "mood_happy_discogs_effnet"

# Minimal schema matching real discogs-effnet-bs64-1.json (predictions + embeddings).
EFFNET_META = {
    "classes": ["Blues---Boogie Woogie", "Electronic---House"],
    "schema": {
        "outputs": [
            {"name": "PartitionedCall:0", "output_purpose": "predictions"},
            {"name": "PartitionedCall:1", "output_purpose": "embeddings"},
        ]
    },
}

HEAD_META = {"classes": ["non_happy", "happy"]}


def test_effnet_with_separate_head_does_not_use_direct_predictions() -> None:
    assert not _use_direct_extractor_predictions(
        EMBEDDINGS_EXTRACTOR_KEY, HEAD_MOOD, EFFNET_META
    )


def test_maest_extractor_uses_direct_predictions() -> None:
    maest_meta = {
        "schema": {
            "outputs": [
                {"name": "PartitionedCall/Identity_13", "output_purpose": "predictions"},
            ]
        }
    }
    assert _use_direct_extractor_predictions(
        "discogs_maest_30s_pw_519l", "genre_discogs519_maest_519l", maest_meta
    )


@pytest.fixture
def fake_essentia_effnet(monkeypatch):
    counters = {"predict2d": 0, "effnet": 0}

    class FakeMonoLoader:
        def __init__(self, **_kwargs):
            pass

        def __call__(self):
            return [0.0]

    class FakeEffnet:
        def __init__(self, **_kwargs):
            pass

        def __call__(self, _audio):
            counters["effnet"] += 1
            return [[1.0] * 1280]

    class FakePredict2D:
        def __init__(self, **_kwargs):
            pass

        def __call__(self, _frames):
            counters["predict2d"] += 1
            return [[0.2, 0.8]]

    fake_std = types.ModuleType("essentia.standard")
    fake_std.MonoLoader = FakeMonoLoader
    fake_std.TensorflowPredictEffnetDiscogs = FakeEffnet
    fake_std.TensorflowPredict2D = FakePredict2D
    fake_pkg = types.ModuleType("essentia")
    fake_pkg.standard = fake_std
    monkeypatch.setitem(sys.modules, "essentia", fake_pkg)
    monkeypatch.setitem(sys.modules, "essentia.standard", fake_std)
    return counters


def test_mood_head_runs_predict2d_not_effnet_predictions(
    fake_essentia_effnet, tmp_path, build_tf_models, make_tf_manager
) -> None:
    models_dir = build_tf_models(
        [EMBEDDINGS_EXTRACTOR_KEY, HEAD_MOOD],
        metadata={
            EMBEDDINGS_EXTRACTOR_KEY: EFFNET_META,
            HEAD_MOOD: HEAD_META,
        },
    )
    mm = make_tf_manager(models_dir)
    backend = EssentiaTensorflowBackend(model_manager=mm)
    wav = tmp_path / "seg.wav"
    wav.write_bytes(b"fake")

    pairs = backend.classifier_activations(
        str(wav), extractor_key=EMBEDDINGS_EXTRACTOR_KEY, head_key=HEAD_MOOD
    )

    assert fake_essentia_effnet["predict2d"] == 1
    assert len(pairs) == 2
    assert pairs[0][0] == "non_happy"
    assert pairs[1][0] == "happy"
