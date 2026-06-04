from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from app.audio.cleanup import AudioCleanupService
from app.audio.ffmpeg import convert_to_wav_pcm
from app.audio.wav_pad import ensure_min_wav_duration
from app.audio.matching import rank_candidates
from app.audio.paths import segment_absolute_path, segment_relative_path
from app.audio.provider import (
    AudioSourceCandidate,
    CleanupResult,
    PlannedSegment,
    TrackContext,
)
from app.audio.segments import plan_segments_for_track
from app.audio.ytdlp_runner import run_download_section, run_search
from app.observability.redact import redact_dict


class YtDlpSegmentProvider:
    def resolve(self, track: TrackContext) -> list[AudioSourceCandidate]:
        query = f"{track.title} {track.primary_artist} audio"
        entries = run_search(query)
        return rank_candidates(track, entries)

    def get_segments(
        self,
        track: TrackContext,
        strategy: str,
        *,
        segment_duration_seconds: float | None = None,
    ) -> list[PlannedSegment]:
        return plan_segments_for_track(
            track,
            strategy,
            segment_duration_seconds=segment_duration_seconds,
        )

    def download_segment(
        self,
        track: TrackContext,
        *,
        job_id: str,
        segment: PlannedSegment,
        source_url: str,
    ) -> tuple[str, str]:
        rel = segment_relative_path(
            track_id=track.track_id,
            job_id=job_id,
            segment_type=segment.segment_type,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
        )
        wav_path = segment_absolute_path(rel)
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = wav_path.with_suffix(".tmp_dl")
        downloaded = run_download_section(
            source_url,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            output_template=tmp,
        )
        try:
            convert_to_wav_pcm(downloaded, wav_path)
            ensure_min_wav_duration(wav_path)
        finally:
            if downloaded.exists():
                downloaded.unlink(missing_ok=True)
            for p in wav_path.parent.glob(f"{tmp.name}*"):
                p.unlink(missing_ok=True)
        file_hash = _file_hash(wav_path)
        return rel, file_hash

    def cleanup(
        self,
        job_id: str | None = None,
        track_id: int | None = None,
    ) -> CleanupResult:
        return AudioCleanupService().cleanup_files(job_id=job_id, track_id=track_id)

    def resolution_json(self, candidates: list[AudioSourceCandidate]) -> str:
        payload = [redact_dict(asdict(c)) for c in candidates]
        return json.dumps(payload)


def source_url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:32]
