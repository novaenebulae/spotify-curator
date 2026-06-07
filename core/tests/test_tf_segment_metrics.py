from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.audio.tensorflow.backend import EssentiaTensorflowBackend


def test_segment_timing_dict_includes_cache_sizes() -> None:
    mm = MagicMock()
    backend = EssentiaTensorflowBackend(model_manager=mm)
    backend.begin_segment_timing()
    backend._predictor_cache[("k",)] = object()
    backend._frames_cache[("f",)] = object()
    timing = backend.consume_segment_timing()

    assert "mono_loader_ms" in timing
    assert "predictor_cache_size" in timing
    assert timing["predictor_cache_size"] == 1
    assert timing["frames_cache_size"] == 1
    assert timing["total_tensorflow_stage_ms"] >= 0


def test_configure_device_cpu_mode(monkeypatch) -> None:
    monkeypatch.setenv("ESSENTIA_TF_DEVICE", "cpu")
    from app.settings.config import settings

    monkeypatch.setattr(settings, "essentia_tf_device", "cpu")

    fake_tf = MagicMock()
    fake_tf.__version__ = "2.15.0"
    fake_tf.config.list_physical_devices.return_value = [MagicMock(name="/physical_device:GPU:0")]

    with patch("app.audio.tensorflow.device._import_tensorflow", return_value=fake_tf):
        from app.audio.tensorflow.device import configure_tensorflow_device

        info = configure_tensorflow_device()

    fake_tf.config.set_visible_devices.assert_called_once_with([], "GPU")
    assert info.device_mode == "cpu"
