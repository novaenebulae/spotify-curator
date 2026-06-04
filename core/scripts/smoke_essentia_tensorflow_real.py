#!/usr/bin/env python3
"""Smoke test for REAL Essentia TensorFlow inference (phase 6.8C).

Proves that, when the minimal model profile is installed, the runners produce
real inference (``inference_mode="real"``) on a short WAV. When models are
missing it reports ``model_missing`` cleanly instead of crashing, and never
emits a stub in production.

Examples (run inside the advanced-analysis Docker service):
    uv run python scripts/smoke_essentia_tensorflow_real.py --require-models
    uv run python scripts/smoke_essentia_tensorflow_real.py --allow-missing
    uv run python scripts/smoke_essentia_tensorflow_real.py --wav-path /tmp/seg.wav
    uv run python scripts/smoke_essentia_tensorflow_real.py --persist --track-id 1
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
import wave
from pathlib import Path
from typing import Any

# Make `app` importable when launched as `python scripts/x.py` (script dir, not
# the core root, lands on sys.path). Mirrors tests/conftest.py.
_CORE_ROOT = Path(__file__).resolve().parents[1]
if str(_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CORE_ROOT))

from app.audio.tensorflow.backend import (  # noqa: E402
    EssentiaTensorflowBackend,
    TensorflowInferenceBackend,
)
from app.audio.tensorflow.classifier_runner import ClassifierRunner  # noqa: E402
from app.audio.tensorflow.embeddings_runner import (  # noqa: E402
    EFFNET_MODEL_KEY,
    EmbeddingsRunner,
)
from app.audio.tensorflow.errors import InferenceError  # noqa: E402
from app.audio.tensorflow.genre_runner import GENRE_MODEL_KEY, GenreRunner  # noqa: E402
from app.audio.tensorflow.model_map import (  # noqa: E402
    EMBEDDINGS_EXTRACTOR_KEY,
    GENRE_EXTRACTOR_KEY,
    GENRE_HEAD_KEY,
)
from app.models_registry import ModelManager, ModelManagerError  # noqa: E402
from app.settings.config import settings  # noqa: E402

DEFAULT_PROFILE = "phase6-minimal"
SMOKE_SAMPLE_RATE = 16000
# 30 s is the project segment cap and the minimum the MAEST 30 s genre model
# needs ("input signal is too short" otherwise).
SMOKE_DURATION_SECONDS = 30


def generate_test_wav(path: Path, *, duration_s: int = SMOKE_DURATION_SECONDS) -> Path:
    """Write a short 16 kHz mono sine WAV (<= 30 s) used as smoke input."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(SMOKE_SAMPLE_RATE * min(duration_s, 30))
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SMOKE_SAMPLE_RATE)
        for i in range(frames):
            value = int(0.6 * 32767 * math.sin(2 * math.pi * 440 * i / SMOKE_SAMPLE_RATE))
            wf.writeframes(struct.pack("<h", value))
    return path


def resolve_wav(wav_path: str | None) -> Path:
    if wav_path:
        candidate = Path(wav_path)
        if not candidate.is_file():
            raise FileNotFoundError(f"--wav-path not found: {candidate}")
        return candidate
    return generate_test_wav(Path(settings.cache_dir) / "smoke" / "tensorflow_real_smoke.wav")


def _genre_available(manager: ModelManager) -> bool:
    try:
        return manager.is_available(GENRE_EXTRACTOR_KEY) and manager.is_available(GENRE_HEAD_KEY)
    except ModelManagerError:
        return False


def run_smoke(
    *,
    manager: ModelManager,
    backend: TensorflowInferenceBackend,
    wav_path: str,
    track_id: int = 1,
    persist: bool = False,
    profile: str = DEFAULT_PROFILE,
) -> dict[str, Any]:
    """Run real inference on a single segment and return a structured report."""
    if not manager.is_available(EMBEDDINGS_EXTRACTOR_KEY):
        try:
            profile_keys = manager.resolve_profile(profile)
        except ModelManagerError:
            profile_keys = [EMBEDDINGS_EXTRACTOR_KEY]
        missing = [k for k in profile_keys if not manager.is_available(k)]
        return {
            "status": "model_missing",
            "profile": profile,
            "missing": missing or [EMBEDDINGS_EXTRACTOR_KEY],
        }

    emb = EmbeddingsRunner(model_manager=manager, backend=backend).run_for_segment(
        segment_id=track_id, wav_path=wav_path
    )
    clf = ClassifierRunner(model_manager=manager, backend=backend).run_for_segment(
        segment_id=track_id, wav_path=wav_path
    )

    genre_top_label: str | None = None
    if _genre_available(manager):
        genre = GenreRunner(model_manager=manager, backend=backend).run_for_segment(
            segment_id=track_id, wav_path=wav_path
        )
        top_k = genre.genre_outputs.get(GENRE_MODEL_KEY, {}).get("top_k") or []
        if top_k:
            genre_top_label = top_k[0].get("label")

    emb_out = emb.embedding_outputs.get(EFFNET_MODEL_KEY, {})
    vector = emb_out.get("vector") or []
    non_empty = bool(vector) or bool(clf.classifier_outputs)
    real = emb.inference_mode == "real" or clf.inference_mode == "real"

    report: dict[str, Any] = {
        "status": "ok" if (real and non_empty) else "no_real_output",
        "wav_path_used": wav_path,
        "embeddings_inference_mode": emb.inference_mode,
        "classifier_inference_mode": clf.inference_mode,
        "embedding_dimension": emb_out.get("dimension"),
        "classifier_count": len(clf.classifier_outputs),
        "genre_top_label": genre_top_label,
        "models_missing": sorted(set(emb.models_missing) | set(clf.models_missing)),
        "persisted": False,
    }

    if persist and vector:
        report["persisted"] = _persist_embedding(
            track_id=track_id, vector=vector, emb_out=emb_out
        )
    return report


def _persist_embedding(*, track_id: int, vector: list[float], emb_out: dict[str, Any]) -> bool:
    """Best-effort persistence of the real embedding; returns success flag."""
    import json

    from sqlalchemy.orm import Session

    from app.database.engine import get_engine
    from app.database.repositories.track_embeddings import (
        TrackEmbeddingsRepository,
        TrackEmbeddingUpsertRow,
    )

    try:
        with Session(get_engine()) as session:
            TrackEmbeddingsRepository().upsert(
                session,
                TrackEmbeddingUpsertRow(
                    track_id=track_id,
                    source="essentia_tensorflow",
                    model_name=str(emb_out.get("model_name") or EFFNET_MODEL_KEY),
                    model_version=emb_out.get("model_version"),
                    dimension=int(emb_out.get("dimension") or len(vector)),
                    vector_json=json.dumps([float(v) for v in vector]),
                    aggregation_method="smoke",
                    segments_used=1,
                    pipeline_version=settings.essentia_tf_pipeline_version,
                    status="success",
                ),
            )
            session.commit()
        return True
    except Exception as exc:  # noqa: BLE001 - smoke persistence is best-effort
        print(f"WARN: persistence failed for track_id={track_id}: {exc}", file=sys.stderr)
        return False


def _print_report(report: dict[str, Any]) -> None:
    for key, value in report.items():
        print(f"  {key}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test for real Essentia TF inference.")
    parser.add_argument("--require-models", action="store_true")
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--track-id", type=int, default=1)
    parser.add_argument("--wav-path", default=None)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args(argv)

    try:
        manager = ModelManager()
    except ModelManagerError as exc:
        print(f"Error: {exc.code}: {exc.message}", file=sys.stderr)
        return 2

    try:
        wav = resolve_wav(args.wav_path)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    backend = EssentiaTensorflowBackend(model_manager=manager)

    try:
        report = run_smoke(
            manager=manager,
            backend=backend,
            wav_path=str(wav),
            track_id=args.track_id,
            persist=args.persist,
            profile=args.profile,
        )
    except InferenceError as exc:
        print(f"SMOKE_FAIL {exc.code}: {exc.message}", file=sys.stderr)
        return 2
    except ModelManagerError as exc:
        print(f"SMOKE_FAIL {exc.code}: {exc.message}", file=sys.stderr)
        return 2

    if report["status"] == "model_missing":
        print(f"SMOKE_MODEL_MISSING profile={report['profile']} missing={report['missing']}")
        if args.require_models and not args.allow_missing:
            return 1
        return 0

    print(f"SMOKE_{'OK' if report['status'] == 'ok' else 'NO_REAL_OUTPUT'}")
    _print_report(report)
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
