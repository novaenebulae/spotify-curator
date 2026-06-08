from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "lambda" / "check_tf_gpu.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_tf_gpu", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_tf_gpu_main_ok_without_require_gpu(monkeypatch) -> None:
    fake_tf = MagicMock()
    fake_tf.__version__ = "2.15.0"
    fake_tf.config.list_physical_devices.return_value = []

    mod = _load_module()
    monkeypatch.delenv("REQUIRE_GPU", raising=False)
    with patch.dict(sys.modules, {"tensorflow": fake_tf}):
        with patch.object(mod.subprocess, "check_output", side_effect=FileNotFoundError("nvidia-smi")):
            assert mod.main() == 0


def test_check_tf_gpu_main_ok_when_tensorflow_missing(monkeypatch) -> None:
    import builtins

    mod = _load_module()
    monkeypatch.delenv("REQUIRE_GPU", raising=False)
    real_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "tensorflow":
            raise ImportError("no tensorflow")
        return real_import(name, *args, **kwargs)

    with patch.object(builtins, "__import__", side_effect=_import):
        assert mod.main() == 0


def test_check_tf_gpu_main_fails_when_required(monkeypatch) -> None:
    fake_tf = MagicMock()
    fake_tf.__version__ = "2.15.0"
    fake_tf.config.list_physical_devices.return_value = []

    mod = _load_module()
    monkeypatch.setenv("REQUIRE_GPU", "true")
    with patch.dict(sys.modules, {"tensorflow": fake_tf}):
        with patch.object(mod.subprocess, "check_output", side_effect=FileNotFoundError("nvidia-smi")):
            assert mod.main() == 1
