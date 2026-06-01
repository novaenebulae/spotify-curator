from __future__ import annotations

from pathlib import Path

from app.settings.config import settings


def audio_segments_root() -> Path:
    return Path(settings.cache_dir) / "audio_segments"


def segment_relative_path(
    *,
    track_id: int,
    job_id: str,
    segment_type: str,
    start_seconds: float,
    end_seconds: float,
) -> str:
    start_i = int(start_seconds * 1000)
    end_i = int(end_seconds * 1000)
    return f"audio_segments/{track_id}/{job_id}_{segment_type}_{start_i}_{end_i}.wav"


def segment_absolute_path(relative_path: str) -> Path:
    rel = relative_path.replace("\\", "/").lstrip("/")
    if rel.startswith("audio_segments/"):
        return Path(settings.cache_dir) / rel
    return Path(settings.cache_dir) / "audio_segments" / rel


def essentia_output_relative(*, track_id: int, segment_id: int, job_id: str) -> str:
    return f"essentia_lowlevel_json/{track_id}/{job_id}_{segment_id}.json"


def essentia_output_absolute(relative_path: str) -> Path:
    rel = relative_path.replace("\\", "/").lstrip("/")
    return Path(settings.cache_dir) / rel
