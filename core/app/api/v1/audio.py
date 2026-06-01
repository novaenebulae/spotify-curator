from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.audio.analysis_job_service import EssentiaLowlevelJobService
from app.audio.cleanup import AudioCleanupService
from app.audio.download_job_service import AudioDownloadJobService
from app.audio.schemas import (
    AudioAnalysisRequest,
    AudioDownloadRequest,
    AudioJobResponse,
    CacheCleanupRequest,
    CacheCleanupResponse,
    PlannedSegmentResponse,
    SegmentPlanRequest,
    SegmentPlanResponse,
    TrackSegmentsResponse,
    TrackSegmentView,
)
from app.audio.hybrid_availability import HybridAvailabilityService
from app.audio.segments import plan_hybrid_for_track, plan_segments_for_track
from app.audio.track_context import load_track_context
from app.settings.config import settings
from app.database.engine import get_engine
from app.database.models_library import Track
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.jobs.status_mapping import map_job_status
from app.observability.errors import ApiError

router = APIRouter(prefix="/audio")
_downloads = AudioDownloadJobService()
_analysis = EssentiaLowlevelJobService()
_segments = TrackSegmentsRepository()
_cleanup = AudioCleanupService()


@router.post("/segments/plan", response_model=SegmentPlanResponse)
def plan_segments(body: SegmentPlanRequest) -> SegmentPlanResponse:
    engine = get_engine()
    analysis_decision: str | None = None
    with Session(engine) as session:
        ctx = load_track_context(session, body.track_id)
        strategy = body.strategy or settings.audio_segment_strategy
        if strategy == "hybrid_deezer_youtube_representative":
            avail = HybridAvailabilityService()
            deezer_ok, deezer_conf = avail.deezer_for_analysis(session, body.track_id)
            planned, analysis_decision = plan_hybrid_for_track(
                ctx,
                segment_duration_seconds=body.segment_duration_seconds,
                deezer_preview_available=deezer_ok,
                youtube_available=body.youtube_available if body.youtube_available is not None else True,
                youtube_confidence=body.youtube_confidence,
                deezer_match_confidence=deezer_conf,
            )
        else:
            planned = plan_segments_for_track(
                ctx,
                strategy,
                segment_duration_seconds=body.segment_duration_seconds,
            )
    return SegmentPlanResponse(
        track_id=body.track_id,
        duration_ms=ctx.duration_ms,
        strategy=body.strategy,
        analysis_decision=analysis_decision,
        segments=[
            PlannedSegmentResponse(
                segment_type=s.segment_type,
                start_seconds=s.start_seconds,
                end_seconds=s.end_seconds,
                duration_seconds=s.duration_seconds,
            )
            for s in planned
        ],
    )


@router.post("/segments/download", response_model=AudioJobResponse)
def start_segment_download(body: AudioDownloadRequest) -> AudioJobResponse:
    job_id = _downloads.start_download_job(
        track_ids=body.track_ids,
        filter_dict=body.filter,
        strategy=body.strategy,
        segment_duration_seconds=body.segment_duration_seconds,
        only_missing=body.only_missing,
        retry_failed=body.retry_failed,
        limit=body.limit,
        provider=body.provider,
    )
    return AudioJobResponse(job_id=job_id, status=map_job_status("queued"))


@router.get("/segments/{track_id}", response_model=TrackSegmentsResponse)
def list_track_segments(track_id: int) -> TrackSegmentsResponse:
    engine = get_engine()
    with Session(engine) as session:
        if session.get(Track, track_id) is None:
            raise ApiError(code="NOT_FOUND", message="Track not found.", status_code=404)
        rows = _segments.list_for_track(session, track_id, include_deleted=False)
        deleted = _segments.list_for_track(session, track_id, include_deleted=True)
        temp_count = sum(1 for s in rows if s.temporary_path and s.deleted_at is None)
        deleted_count = sum(1 for s in deleted if s.deleted_at is not None)
    return TrackSegmentsResponse(
        track_id=track_id,
        segments=[
            TrackSegmentView(
                id=s.id,
                segment_type=s.segment_type,
                start_seconds=s.start_seconds,
                end_seconds=s.end_seconds,
                duration_seconds=s.duration_seconds,
                source=s.source,
                has_file=bool(s.temporary_path and s.deleted_at is None),
                file_hash=s.file_hash,
                features_available=bool(s.features_json),
                deleted_at=s.deleted_at.isoformat() if s.deleted_at else None,
                created_at=s.created_at.isoformat() if s.created_at else "",
            )
            for s in rows
        ],
        cleanup={
            "temporary_files_count": temp_count,
            "deleted_count": deleted_count,
        },
    )


@router.post("/analysis/lowlevel", response_model=AudioJobResponse)
def start_lowlevel_analysis(body: AudioAnalysisRequest) -> AudioJobResponse:
    job_id = _analysis.start_analysis_job(
        track_ids=body.track_ids,
        filter_dict=body.filter,
        only_missing=body.only_missing,
        retry_failed=body.retry_failed,
        force_refresh=body.force_refresh,
        limit=body.limit,
        cleanup_after=body.cleanup_after,
        require_existing_segments=body.require_existing_segments,
    )
    return AudioJobResponse(job_id=job_id, status=map_job_status("queued"))


@router.post("/cache/cleanup", response_model=CacheCleanupResponse)
def cleanup_audio_cache(body: CacheCleanupRequest) -> CacheCleanupResponse:
    result = _cleanup.cleanup_orphan_files(dry_run=body.dry_run)
    if not body.dry_run:
        extra = _cleanup.cleanup_files(
            dry_run=False,
            older_than_hours=body.older_than_hours,
            include_failed=body.include_failed,
        )
        result.matched_files += extra.matched_files
        result.deleted_files += extra.deleted_files
        result.freed_bytes += extra.freed_bytes
        result.errors.extend(extra.errors)
    return CacheCleanupResponse(
        dry_run=body.dry_run,
        matched_files=result.matched_files,
        deleted_files=result.deleted_files,
        freed_bytes=result.freed_bytes,
        errors=result.errors,
    )
