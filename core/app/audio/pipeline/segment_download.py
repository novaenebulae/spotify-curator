from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.audio.deezer_preview_download import download_deezer_preview_segment
from app.audio.provider import PlannedSegment, TrackContext
from app.audio.track_context import load_track_context
from app.audio.ytdlp_provider import YtDlpSegmentProvider, source_url_hash
from app.database.models_audio import AudioDownloadJob, TrackSegment
from app.database.repositories.audio_download_jobs import AudioDownloadJobsRepository
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.settings.config import settings


def planned_segment_from_dict(data: dict[str, Any]) -> PlannedSegment:
    return PlannedSegment(
        segment_type=str(data.get("segment_type", "A")),
        start_seconds=float(data["start_seconds"]),
        end_seconds=float(data["end_seconds"]),
        duration_seconds=float(data["duration_seconds"]),
        strategy=str(data.get("strategy", "abc_default")),
        source=str(data.get("source", "youtube")),
        source_quality=str(data.get("source_quality", "youtube_representative")),
        match_confidence=float(data.get("match_confidence", 1.0)),
        analysis_decision=str(data.get("analysis_decision", "")),
    )


def download_planned_segment(
    session: Session,
    *,
    ctx: TrackContext,
    job_id: str,
    track_id: int,
    planned: PlannedSegment,
    provider: Any,
    is_test: bool,
    selected_source: Any | None,
    deezer_preview_url: str | None,
    download_job_id: int | None,
) -> tuple[int, str]:
    """Persist one segment row and return (segment_id, source)."""
    segments_repo = TrackSegmentsRepository()
    now = datetime.now(tz=UTC).replace(tzinfo=None)

    if planned.source == "deezer_preview":
        if not deezer_preview_url:
            raise RuntimeError("Deezer preview URL missing for segment download")
        rel, fhash = download_deezer_preview_segment(
            ctx,
            job_id=job_id,
            segment=planned,
            preview_url=deezer_preview_url,
        )
        source = "deezer_preview"
        url_hash = source_url_hash(deezer_preview_url)
    elif is_test:
        rel, fhash = provider.materialize_segment(ctx, job_id=job_id, segment=planned)
        source = selected_source.source if selected_source else "test"
        url_hash = source_url_hash(selected_source.url) if selected_source else None
    else:
        if selected_source is None:
            raise RuntimeError("No YouTube source for segment download")
        rel, fhash = provider.download_segment(
            ctx,
            job_id=job_id,
            segment=planned,
            source_url=selected_source.url,
        )
        source = selected_source.source
        url_hash = source_url_hash(selected_source.url)

    row = TrackSegment(
        track_id=track_id,
        download_job_id=download_job_id,
        start_seconds=planned.start_seconds,
        end_seconds=planned.end_seconds,
        duration_seconds=planned.duration_seconds,
        segment_type=planned.segment_type,
        source=source,
        source_quality=planned.source_quality,
        source_url_hash=url_hash,
        temporary_path=rel,
        file_hash=fhash,
        confidence=planned.match_confidence,
        created_at=now,
    )
    segments_repo.insert(session, row)
    session.flush()
    return row.id, source


def create_audio_download_job_row(
    session: Session,
    *,
    job_id: str,
    track_id: int,
    provider_name: str,
    attempt_count: int,
) -> int:
    repo = AudioDownloadJobsRepository()
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    dl_row = AudioDownloadJob(
        job_id=job_id,
        track_id=track_id,
        provider=provider_name,
        status="running",
        attempt_count=attempt_count,
        max_attempts=settings.audio_download_max_retries,
        rate_limited=False,
        created_at=now,
        started_at=now,
    )
    repo.insert(session, dl_row)
    session.flush()
    return dl_row.id
