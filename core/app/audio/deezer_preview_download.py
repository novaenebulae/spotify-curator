from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import httpx

from app.audio.paths import segment_absolute_path, segment_relative_path
from app.audio.provider import PlannedSegment, TrackContext
from app.audio.ffmpeg import convert_to_wav_pcm
from app.audio.wav_pad import MAEST_MIN_SECONDS, ensure_min_wav_duration
from app.settings.config import settings


def download_deezer_preview_segment(
    track: TrackContext,
    *,
    job_id: str,
    segment: PlannedSegment,
    preview_url: str,
    transport: httpx.BaseTransport | None = None,
) -> tuple[str, str]:
    rel = segment_relative_path(
        track_id=track.track_id,
        job_id=job_id,
        segment_type=segment.segment_type,
        start_seconds=segment.start_seconds,
        end_seconds=segment.end_seconds,
    )
    dest = segment_absolute_path(rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_mp3 = dest.with_suffix(".mp3.part")
    max_bytes = int(settings.audio_segment_max_seconds * 320_000)

    with httpx.Client(timeout=settings.deezer_timeout_seconds, transport=transport) as client:
        with client.stream("GET", preview_url) as resp:
            resp.raise_for_status()
            written = 0
            with tmp_mp3.open("wb") as out:
                for chunk in resp.iter_bytes():
                    if not chunk:
                        continue
                    out.write(chunk)
                    written += len(chunk)
                    if written >= max_bytes:
                        break

    max_dur = min(segment.duration_seconds, settings.audio_segment_max_seconds)
    trimmed = dest.with_suffix(".trimmed.mp3")
    try:
        _ffmpeg_trim(tmp_mp3, trimmed, duration_seconds=max_dur)
        convert_to_wav_pcm(trimmed, dest)
    except Exception:
        convert_to_wav_pcm(tmp_mp3, dest)
    ensure_min_wav_duration(dest, min_seconds=MAEST_MIN_SECONDS)
    for p in (tmp_mp3, trimmed):
        if p.exists():
            p.unlink(missing_ok=True)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()[:32]
    return rel, digest


def _ffmpeg_trim(src: Path, dest: Path, *, duration_seconds: float) -> None:
    dur = min(duration_seconds, settings.audio_segment_max_seconds)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-t",
        str(dur),
        "-acodec",
        "copy",
        str(dest),
    ]
    subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        timeout=settings.ffmpeg_timeout_seconds,
    )
