#!/usr/bin/env python3
"""Smoke check for TensorFlow model registry (no heavy inference in phase 6.4)."""

from __future__ import annotations

import sys
import wave
from pathlib import Path

# Make `app` importable when launched as `python scripts/x.py` (script dir, not
# the core root, lands on sys.path). Mirrors tests/conftest.py.
_CORE_ROOT = Path(__file__).resolve().parents[1]
if str(_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CORE_ROOT))

from app.models_registry import ModelRegistry  # noqa: E402
from app.settings.config import settings  # noqa: E402


def _write_short_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000)


def main() -> int:
    registry = ModelRegistry()
    rows, summary = registry.scan()
    print(f"models_dir={settings.models_dir}")
    print(f"summary={summary.to_dict()}")
    print(f"status_only={registry.should_run_status_only()}")

    wav_path = Path(settings.cache_dir) / "smoke" / "tensorflow_smoke.wav"
    _write_short_wav(wav_path)
    print(f"smoke_wav={wav_path} bytes={wav_path.stat().st_size}")

    if registry.should_run_status_only():
        print("SMOKE_OK status_only (models missing or ESSENTIA_TENSORFLOW_STATUS_ONLY)")
        return 0

    required = [r for r in rows if r.status == "available"]
    print(f"available_models={len(required)}")
    if not required:
        print("SMOKE_SKIP no available models")
        return 0

    print("SMOKE_OK registry and wav ready for future inference")
    return 0


if __name__ == "__main__":
    sys.exit(main())
