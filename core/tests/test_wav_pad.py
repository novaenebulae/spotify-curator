from __future__ import annotations

import shutil
import wave
from pathlib import Path

import pytest

from app.audio.wav_pad import MAEST_MIN_SECONDS, ensure_min_wav_duration, wav_duration_seconds


def _write_silent_wav(path: Path, *, duration_sec: float, rate: int = 16_000) -> None:
    nframes = max(1, int(duration_sec * rate))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * nframes)


def test_maest_threshold_treats_29976_as_too_short(tmp_path: Path) -> None:
    wav = tmp_path / "preview.wav"
    _write_silent_wav(wav, duration_sec=29.976)
    dur = wav_duration_seconds(wav)
    assert dur < MAEST_MIN_SECONDS


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_ensure_min_wav_duration_pads_below_30_seconds(tmp_path: Path) -> None:
    wav = tmp_path / "preview.wav"
    _write_silent_wav(wav, duration_sec=29.976)
    final = ensure_min_wav_duration(wav)
    assert final >= MAEST_MIN_SECONDS
