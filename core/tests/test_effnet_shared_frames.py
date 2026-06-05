"""Verify ClassifierRunner uses a single EffNet frame extraction for all EffNet heads."""

from __future__ import annotations

import sys
import types

import pytest

from app.audio.tensorflow.backend import EssentiaTensorflowBackend
from app.audio.tensorflow.classifier_runner import ClassifierRunner
from app.audio.tensorflow.model_map import EMBEDDINGS_EXTRACTOR_KEY

HEAD_A = "mood_happy_discogs_effnet"
HEAD_B = "mood_sad_discogs_effnet"
HEAD_C = "danceability_discogs_effnet"


class _Counters:
    def __init__(self) -> None:
        self.monoloader_init = 0
        self.effnet_init = 0
        self.effnet_calls = 0
        self.predict2d_init = 0
        self.predict2d_calls = 0


@pytest.fixture
def fake_essentia(monkeypatch):
    counters = _Counters()

    class FakeMonoLoader:
        def __init__(self, **_kwargs):
            counters.monoloader_init += 1

        def __call__(self):
            return [0.0]

    class FakeEffnet:
        def __init__(self, **_kwargs):
            counters.effnet_init += 1

        def __call__(self, _audio):
            counters.effnet_calls += 1
            return [[1.0] * 1280 for _ in range(3)]

    class FakePredict2D:
        def __init__(self, **_kwargs):
            counters.predict2d_init += 1

        def __call__(self, _frames):
            counters.predict2d_calls += 1
            return [[0.5, 0.5] for _ in range(3)]

    fake_std = types.ModuleType("essentia.standard")
    fake_std.MonoLoader = FakeMonoLoader
    fake_std.TensorflowPredictEffnetDiscogs = FakeEffnet
    fake_std.TensorflowPredict2D = FakePredict2D

    fake_pkg = types.ModuleType("essentia")
    fake_pkg.standard = fake_std

    monkeypatch.setitem(sys.modules, "essentia", fake_pkg)
    monkeypatch.setitem(sys.modules, "essentia.standard", fake_std)
    return counters


def test_classifier_runner_single_effnet_extract(
    fake_essentia, build_tf_models, make_tf_manager, tmp_path
):
    models_dir = build_tf_models(
        [EMBEDDINGS_EXTRACTOR_KEY, HEAD_A, HEAD_B, HEAD_C]
    )
    mm = make_tf_manager(models_dir)
    backend = EssentiaTensorflowBackend(model_manager=mm)
    wav = tmp_path / "seg.wav"
    wav.write_bytes(b"\x00\x01" * 100)

    result = ClassifierRunner(model_manager=mm, backend=backend).run_for_segment(
        segment_id=1, wav_path=str(wav)
    )

    assert "mood_happy" in result.classifier_outputs
    assert "mood_sad" in result.classifier_outputs
    assert "danceability" in result.classifier_outputs
    assert fake_essentia.effnet_calls == 1
    assert fake_essentia.monoloader_init == 1
    assert fake_essentia.predict2d_calls == 3
