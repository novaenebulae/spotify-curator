#!/usr/bin/env python3
"""CLI to download / verify Essentia TensorFlow models from the versioned manifest.

Examples:
    uv run python scripts/download_essentia_models.py --profile phase6-minimal --accept-license
    uv run python scripts/download_essentia_models.py --profile phase6-recommended --accept-license
    uv run python scripts/download_essentia_models.py --model discogs_effnet_bs64 --accept-license
    uv run python scripts/download_essentia_models.py --verify-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make `app` importable when launched as `python scripts/x.py` (script dir, not
# the core root, lands on sys.path). Mirrors tests/conftest.py.
_CORE_ROOT = Path(__file__).resolve().parents[1]
if str(_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CORE_ROOT))

from app.models_registry import ModelManager, ModelManagerError  # noqa: E402

PROFILES = ("phase6-minimal", "phase6-recommended", "phase6-full")


def _print_license(manager: ModelManager) -> None:
    info = manager.license
    print(f"License: {info.get('name', 'CC BY-NC-SA 4.0')}")
    if info.get("source_url"):
        print(f"License source: {info['source_url']}")
    print("Non-commercial use. Explicit acceptance required before download.")


def _verify(manager: ModelManager, *, profile: str | None, model: str | None) -> int:
    if model:
        result = manager.verify_model(model)
        rows = [result]
    else:
        target = profile or manager.default_profile
        result = manager.verify_profile(target)
        rows = result["models"]
        print(f"Verify profile: {target}")
    missing = 0
    for row in rows:
        if row["status"] != "available":
            missing += 1
        print(
            f"  {row['model_key']}: {row['status']} "
            f"(weights={row['weights_exists']}, metadata={row['metadata_exists']})"
        )
    print(f"Done. {len(rows) - missing}/{len(rows)} available.")
    return 0 if missing == 0 else 1


def _download(manager: ModelManager, *, profile: str | None, model: str | None, force: bool) -> int:
    if model:
        result = manager.download_model(model, accept_license=True, force=force)
        rows = result["downloaded"]
    else:
        target = profile or manager.default_profile
        result = manager.download_profile(target, accept_license=True, force=force)
        rows = result["models"]
        print(f"Download profile: {target}")
    for row in rows:
        actions = ", ".join(row["downloaded"]) or "already present"
        print(f"  {row['model_key']}: {row['status']} [{actions}]")
    print(f"Done. {len(rows)} model(s) processed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download/verify Essentia TensorFlow models.")
    parser.add_argument("--profile", choices=PROFILES, default=None)
    parser.add_argument("--model", default=None, help="Single model_key from the manifest.")
    parser.add_argument("--accept-license", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)

    try:
        manager = ModelManager()
    except ModelManagerError as exc:
        print(f"Error: {exc.code}: {exc.message}", file=sys.stderr)
        return 1

    _print_license(manager)

    try:
        if args.verify_only:
            return _verify(manager, profile=args.profile, model=args.model)
        if not args.accept_license:
            print(
                "Error: MODEL_LICENSE_NOT_ACCEPTED: pass --accept-license to download.",
                file=sys.stderr,
            )
            return 2
        return _download(manager, profile=args.profile, model=args.model, force=args.force)
    except ModelManagerError as exc:
        print(f"Error: {exc.code}: {exc.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
