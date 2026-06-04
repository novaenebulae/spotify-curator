#!/usr/bin/env python3
"""Entrypoint for essentia-tensorflow-worker Docker service."""

import sys
from pathlib import Path

# Make `app` importable when launched as `python scripts/x.py` (script dir, not
# the core root, lands on sys.path). Mirrors tests/conftest.py.
_CORE_ROOT = Path(__file__).resolve().parents[1]
if str(_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CORE_ROOT))

from app.workers.essentia_tensorflow_worker import EssentiaTensorflowWorker  # noqa: E402


def main() -> None:
    EssentiaTensorflowWorker().run_forever()


if __name__ == "__main__":
    main()
