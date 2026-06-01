from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.audio.errors import FfmpegError
from app.settings.config import settings


@dataclass(frozen=True)
class FfmpegCommand:
    argv: list[str]
    output_path: str


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def build_wav_convert_command(input_path: Path, output_path: Path) -> FfmpegCommand:
    argv = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-acodec",
        "pcm_s16le",
        "-ar",
        "44100",
        "-ac",
        "2",
        str(output_path),
    ]
    return FfmpegCommand(argv=argv, output_path=str(output_path))


def convert_to_wav_pcm(input_path: Path, output_path: Path) -> Path:
    if not ffmpeg_available():
        raise FfmpegError("FFMPEG_NOT_FOUND", "ffmpeg binary not found on PATH")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_wav_convert_command(input_path, output_path)
    try:
        proc = subprocess.run(
            cmd.argv,
            capture_output=True,
            text=True,
            timeout=settings.ffmpeg_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise FfmpegError("FFMPEG_TIMEOUT", "ffmpeg timed out", retryable=True) from e
    if proc.returncode != 0:
        raise FfmpegError(
            "FFMPEG_FAILED",
            (proc.stderr or proc.stdout or "ffmpeg failed")[:500],
        )
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise FfmpegError("FFMPEG_EMPTY_OUTPUT", "ffmpeg produced no output file")
    return output_path
