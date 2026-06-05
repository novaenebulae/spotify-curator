"""EffNet caching invariants for :class:`EssentiaTensorflowBackend`.

A fake ``essentia.standard`` module is injected so we can count how many times
the extractor / heads / audio loader are built and run, without importing the
real (Docker-only) Essentia. The recommended pattern is to compute the EffNet
frames once per segment and reuse them across all heads.
"""

from __future__ import annotations

import sys
import types

import pytest

from app.audio.tensorflow.backend import EssentiaTensorflowBackend
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
        def __init__(self, **kwargs):
            counters.monoloader_init += 1
            assert "filename" in kwargs, "MonoLoader must receive filename at construction"

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


def test_effnet_frames_computed_once_per_segment(fake_essentia, build_tf_models, make_tf_manager):
    models_dir = build_tf_models([EMBEDDINGS_EXTRACTOR_KEY, HEAD_A, HEAD_B])
    mm = make_tf_manager(models_dir)
    backend = EssentiaTensorflowBackend(model_manager=mm)

    wav = "/segments/track-1.wav"
    backend.embeddings(wav, extractor_key=EMBEDDINGS_EXTRACTOR_KEY)
    backend.classifier_activations(wav, extractor_key=EMBEDDINGS_EXTRACTOR_KEY, head_key=HEAD_A)
    backend.classifier_activations(wav, extractor_key=EMBEDDINGS_EXTRACTOR_KEY, head_key=HEAD_B)

    # Extractor built and run exactly once, reused by embeddings() + both heads.
    assert fake_essentia.effnet_init == 1
    assert fake_essentia.effnet_calls == 1
    # Audio decoded once for the segment.
    assert fake_essentia.monoloader_init == 1
    # One head graph per distinct head, each run once.
    assert fake_essentia.predict2d_init == 2
    assert fake_essentia.predict2d_calls == 2


def test_distinct_segment_reruns_extractor_but_reuses_predictor(
    fake_essentia, build_tf_models, make_tf_manager
):
    models_dir = build_tf_models([EMBEDDINGS_EXTRACTOR_KEY, HEAD_A])
    mm = make_tf_manager(models_dir)
    backend = EssentiaTensorflowBackend(model_manager=mm)

    backend.classifier_activations(
        "/segments/a.wav", extractor_key=EMBEDDINGS_EXTRACTOR_KEY, head_key=HEAD_A
    )
    backend.classifier_activations(
        "/segments/b.wav", extractor_key=EMBEDDINGS_EXTRACTOR_KEY, head_key=HEAD_A
    )

    # Predictor graphs are memoized across segments (built once)...
    assert fake_essentia.effnet_init == 1
    assert fake_essentia.predict2d_init == 1
    # ...but a new WAV re-runs the extractor and head (frames are WAV-scoped).
    assert fake_essentia.effnet_calls == 2
    assert fake_essentia.predict2d_calls == 2
    assert fake_essentia.monoloader_init == 2


def test_run_effnet_classifier_heads_single_extract(
    fake_essentia, build_tf_models, make_tf_manager
):
    models_dir = build_tf_models([EMBEDDINGS_EXTRACTOR_KEY, HEAD_A, HEAD_B, HEAD_C])
    mm = make_tf_manager(models_dir)
    backend = EssentiaTensorflowBackend(model_manager=mm)

    wav = "/segments/track-1.wav"
    backend.run_effnet_classifier_heads(wav, [HEAD_A, HEAD_B, HEAD_C])

    assert fake_essentia.effnet_init == 1
    assert fake_essentia.effnet_calls == 1
    assert fake_essentia.monoloader_init == 1
    assert fake_essentia.predict2d_init == 3
    assert fake_essentia.predict2d_calls == 3
