"""Verify Essentia TensorFlow runtime and optional NVIDIA GPU visibility."""

from __future__ import annotations

import os
import subprocess
import sys


def _check_essentia_algorithms() -> list[str]:
    import essentia.standard as es  # type: ignore[import-not-found]

    required = (
        "TensorflowPredictEffnetDiscogs",
        "TensorflowPredict2D",
        "TensorflowPredictMAEST",
    )
    missing: list[str] = []
    for name in required:
        if not hasattr(es, name):
            missing.append(name)
    return missing


def main() -> int:
    ld_path = os.getenv("LD_LIBRARY_PATH", "")
    print("LD_LIBRARY_PATH:", ld_path or "(unset)")

    try:
        import essentia  # type: ignore[import-not-found]

        print("Essentia:", essentia.__version__)
    except Exception as exc:  # noqa: BLE001
        print("ERROR: essentia import failed:", exc, file=sys.stderr)
        return 1

    missing_algos = _check_essentia_algorithms()
    if missing_algos:
        print("ERROR: missing Essentia TensorFlow algorithms:", missing_algos, file=sys.stderr)
        return 1
    print("Essentia TensorFlow algorithms OK")

    nvidia_ok = False
    try:
        out = subprocess.check_output(["nvidia-smi"], text=True)
        print(out)
        nvidia_ok = True
    except Exception as exc:  # noqa: BLE001
        print("nvidia-smi unavailable:", exc)

    require_gpu = os.getenv("REQUIRE_GPU", "false").lower() == "true"
    if require_gpu and not nvidia_ok:
        print("ERROR: REQUIRE_GPU=true but nvidia-smi failed", file=sys.stderr)
        return 1

    print("ESSENTIA_TF_OK=true")
    print("GPU_VISIBLE=" + str(nvidia_ok).lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
