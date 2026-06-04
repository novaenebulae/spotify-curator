from __future__ import annotations

import pytest

from app.audio.tensorflow.classifier_runner import ClassifierRunner
from app.audio.tensorflow.errors import STUB_INFERENCE_FORBIDDEN, InferenceError
from app.audio.tensorflow.guard import stubs_allowed
from app.settings.config import settings


def _wav(tmp_path) -> str:
    path = tmp_path / "seg.wav"
    path.write_bytes(b"\x00\x01\x02\x03")
    return str(path)


def _set_env(monkeypatch, *, app_env: str, allow_stubs: bool) -> None:
    monkeypatch.setattr(settings, "app_env", app_env)
    monkeypatch.setattr(settings, "essentia_tf_allow_stubs_in_tests", allow_stubs)


def test_stubs_allowed_requires_test_env_and_flag(monkeypatch) -> None:
    _set_env(monkeypatch, app_env="production", allow_stubs=True)
    assert stubs_allowed() is False
    _set_env(monkeypatch, app_env="test", allow_stubs=False)
    assert stubs_allowed() is False
    _set_env(monkeypatch, app_env="test", allow_stubs=True)
    assert stubs_allowed() is True


def test_classifier_without_backend_forbidden_outside_tests(
    tmp_path, monkeypatch, build_tf_models, make_tf_manager
) -> None:
    _set_env(monkeypatch, app_env="production", allow_stubs=False)
    models_dir = build_tf_models(["discogs_effnet_bs64", "mood_happy_discogs_effnet"])
    mm = make_tf_manager(models_dir)

    runner = ClassifierRunner(model_manager=mm, backend=None)
    with pytest.raises(InferenceError) as exc:
        runner.run_for_segment(segment_id=1, wav_path=_wav(tmp_path))
    assert exc.value.code == STUB_INFERENCE_FORBIDDEN


def test_classifier_stub_allowed_in_test_env(
    tmp_path, monkeypatch, build_tf_models, make_tf_manager
) -> None:
    _set_env(monkeypatch, app_env="test", allow_stubs=True)
    models_dir = build_tf_models(["discogs_effnet_bs64", "mood_happy_discogs_effnet"])
    mm = make_tf_manager(models_dir)

    runner = ClassifierRunner(model_manager=mm, backend=None)
    result = runner.run_for_segment(segment_id=1, wav_path=_wav(tmp_path))
    assert result.inference_mode == "stub"
    assert "mood_happy" in result.classifier_outputs
    assert result.classifier_outputs["mood_happy"]["inference_mode"] == "stub"
