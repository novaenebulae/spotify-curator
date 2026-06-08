"""Legacy TensorFlow Python GPU probe (optional when only essentia-tensorflow is installed)."""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    try:
        import tensorflow as tf
    except ImportError:
        print(
            "WARNING: tensorflow Python package not installed; "
            "use scripts/lambda/check_essentia_tf.py for Essentia GPU checks",
            file=sys.stderr,
        )
        require_gpu = os.getenv("REQUIRE_GPU", "false").lower() == "true"
        if require_gpu:
            print("ERROR: REQUIRE_GPU=true but tensorflow is not importable", file=sys.stderr)
            return 1
        return 0

    print("TensorFlow:", tf.__version__)
    gpus = tf.config.list_physical_devices("GPU")
    print("TensorFlow GPUs:", gpus)

    try:
        out = subprocess.check_output(["nvidia-smi"], text=True)
        print(out)
    except Exception as exc:  # noqa: BLE001
        print("nvidia-smi unavailable:", exc)

    require_gpu = os.getenv("REQUIRE_GPU", "false").lower() == "true"
    if require_gpu and not gpus:
        print("ERROR: REQUIRE_GPU=true but TensorFlow sees no GPU", file=sys.stderr)
        return 1

    print("GPU_OK=" + str(bool(gpus)).lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
