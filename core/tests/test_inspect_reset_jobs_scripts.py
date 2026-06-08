from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str):
    path = REPO_ROOT / "core" / "scripts" / name
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_inspect_jobs_script_has_main() -> None:
    mod = _load_script("inspect_jobs.py")
    assert callable(mod.main)


def test_reset_stale_jobs_script_has_main() -> None:
    mod = _load_script("reset_stale_jobs.py")
    assert callable(mod.main)
