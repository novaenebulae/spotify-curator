from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "lambda" / "check_essentia_tf.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_essentia_tf", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_essentia_tf_main_ok(monkeypatch) -> None:
    fake_es = MagicMock()
    fake_es.TensorflowPredictEffnetDiscogs = MagicMock()
    fake_es.TensorflowPredict2D = MagicMock()
    fake_es.TensorflowPredictMAEST = MagicMock()
    fake_essentia = MagicMock()
    fake_essentia.__version__ = "2.1b6"
    fake_std = MagicMock()
    fake_std.TensorflowPredictEffnetDiscogs = MagicMock()
    fake_std.TensorflowPredict2D = MagicMock()
    fake_std.TensorflowPredictMAEST = MagicMock()

    mod = _load_module()
    monkeypatch.delenv("REQUIRE_GPU", raising=False)
    with patch.dict(
        sys.modules,
        {
            "essentia": fake_essentia,
            "essentia.standard": fake_std,
        },
    ):
        with patch.object(mod.subprocess, "check_output", return_value="GPU 0"):
            assert mod.main() == 0


def test_check_essentia_tf_fails_when_require_gpu_and_no_nvidia(monkeypatch) -> None:
    fake_essentia = MagicMock()
    fake_essentia.__version__ = "2.1b6"
    fake_std = MagicMock()
    fake_std.TensorflowPredictEffnetDiscogs = MagicMock()
    fake_std.TensorflowPredict2D = MagicMock()
    fake_std.TensorflowPredictMAEST = MagicMock()

    mod = _load_module()
    monkeypatch.setenv("REQUIRE_GPU", "true")
    with patch.dict(
        sys.modules,
        {
            "essentia": fake_essentia,
            "essentia.standard": fake_std,
        },
    ):
        with patch.object(mod.subprocess, "check_output", side_effect=FileNotFoundError("nvidia-smi")):
            assert mod.main() == 1
