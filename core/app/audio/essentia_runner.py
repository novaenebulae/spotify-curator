from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from app.audio.errors import EssentiaError
from app.audio.paths import essentia_output_absolute, essentia_output_relative
from app.settings.config import settings


def essentia_binary() -> str:
    return shutil.which("essentia_streaming_extractor_music") or "essentia_streaming_extractor_music"


def run_essentia_lowlevel(
    *,
    input_wav: Path,
    track_id: int,
    segment_id: int,
    job_id: str,
) -> tuple[Path, str]:
    if not input_wav.is_file():
        raise EssentiaError("ESSENTIA_INPUT_MISSING", f"Input WAV not found: {input_wav.name}")
    rel_out = essentia_output_relative(track_id=track_id, segment_id=segment_id, job_id=job_id)
    out_path = essentia_output_absolute(rel_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    profile = Path(settings.essentia_lowlevel_profile)
    if not profile.is_file():
        raise EssentiaError("ESSENTIA_PROFILE_MISSING", f"Profile not found: {profile.name}")
    argv = [
        essentia_binary(),
        str(input_wav),
        str(out_path),
        str(profile),
    ]
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=settings.essentia_lowlevel_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise EssentiaError("ESSENTIA_TIMEOUT", "Essentia timed out", retryable=True) from e
    if proc.returncode != 0:
        raise EssentiaError(
            "ESSENTIA_FAILED",
            (proc.stderr or proc.stdout or "essentia failed")[:500],
        )
    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise EssentiaError("ESSENTIA_EMPTY_OUTPUT", "Essentia produced no JSON output")
    with out_path.open(encoding="utf-8") as f:
        json.load(f)
    return out_path, rel_out
