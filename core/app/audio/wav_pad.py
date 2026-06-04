from __future__ import annotations

import subprocess
import wave
from pathlib import Path

from app.settings.config import settings

# MAEST 30s models reject inputs slightly below 30s wall-clock seconds.
MAEST_MIN_SECONDS = 30.0
# Pad target slightly above 30s so ffmpeg rounding (e.g. 29.976s previews) still passes MAEST.
MAEST_PAD_TARGET_SECONDS = 30.05


def wav_duration_seconds(path: Path) -> float:
    """Wall-clock duration of a PCM WAV file."""
    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate()
        if rate <= 0:
            return 0.0
        return wf.getnframes() / float(rate)


def ensure_min_wav_duration(
    path: Path,
    *,
    min_seconds: float = MAEST_MIN_SECONDS,
    target_seconds: float = MAEST_PAD_TARGET_SECONDS,
) -> float:
    """Pad short segments so MAEST / genre extractors accept the WAV. Returns final duration."""
    current = wav_duration_seconds(path)
    if current >= min_seconds:
        return current
    rate = 16_000
    channels = 1
    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate() or rate
        channels = wf.getnchannels() or channels
    padded = path.with_suffix(".pad.wav")
    pad_target = max(target_seconds, min_seconds)
    pad_dur = max(0.0, pad_target - current)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-af",
            f"apad=pad_dur={pad_dur:.3f}",
            "-t",
            str(pad_target),
            "-ar",
            str(rate),
            "-ac",
            str(channels),
            str(padded),
        ],
        check=True,
        capture_output=True,
        timeout=settings.ffmpeg_timeout_seconds,
    )
    padded.replace(path)
    return wav_duration_seconds(path)
