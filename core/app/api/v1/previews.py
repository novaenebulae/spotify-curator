from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.repositories.track_previews import TrackPreviewsRepository
from app.jobs.status_mapping import map_job_status
from app.observability.errors import ApiError
from app.previews.resolve_job_service import PreviewResolveJobService
from app.previews.stream import fetch_track_preview_audio

router = APIRouter()
_resolve_jobs = PreviewResolveJobService()
_previews = TrackPreviewsRepository()


class PreviewResolveRequest(BaseModel):
    only_missing: bool = True
    force_refresh: bool = False
    limit: int | None = None
    track_ids: list[int] | None = None


class PreviewResolveResponse(BaseModel):
    job_id: str
    status: str


class TrackPreviewResponse(BaseModel):
    track_id: int
    provider: str | None = None
    preview_url: str | None = None
    playback_url: str | None = None
    match_confidence: float | None = None
    match_strategy: str | None = None
    is_available: bool = False
    resolve_job_id: str | None = None


class PreviewCoverageResponse(BaseModel):
    track_count: int
    with_any_preview: int
    with_deezer_preview: int
    missing_preview: int
    failed_preview: int
    coverage_percent: float


@router.get("/tracks/{track_id}/preview", response_model=TrackPreviewResponse)
def get_track_preview(
    track_id: int,
    resolve_if_missing: bool = Query(False),
) -> TrackPreviewResponse:
    engine = get_engine()
    with Session(engine) as session:
        row = _previews.get_best_for_track(session, track_id)
        if row is not None:
            return TrackPreviewResponse(
                track_id=track_id,
                provider=row.provider,
                preview_url=row.preview_url,
                playback_url=f"/api/v1/tracks/{track_id}/preview/stream",
                match_confidence=row.match_confidence,
                match_strategy=row.match_strategy,
                is_available=bool(row.is_available),
            )
        if resolve_if_missing:
            job_id = _resolve_jobs.start_resolve_job(only_missing=True, limit=1)
            return TrackPreviewResponse(
                track_id=track_id,
                is_available=False,
                resolve_job_id=job_id,
            )
    return TrackPreviewResponse(track_id=track_id, is_available=False)


@router.get("/tracks/{track_id}/preview/stream")
def stream_track_preview(track_id: int) -> Response:
    """Same-origin audio stream for UI playback (avoids CORB on Deezer CDN URLs)."""
    engine = get_engine()
    with Session(engine) as session:
        data, media_type = fetch_track_preview_audio(session, track_id)
    return Response(content=data, media_type=media_type)


@router.post("/previews/resolve", response_model=PreviewResolveResponse)
def start_preview_resolve(body: PreviewResolveRequest) -> PreviewResolveResponse:
    job_id = _resolve_jobs.start_resolve_job(
        only_missing=body.only_missing,
        force_refresh=body.force_refresh,
        limit=body.limit,
        track_ids=body.track_ids,
    )
    return PreviewResolveResponse(job_id=job_id, status=map_job_status("queued"))


@router.get("/previews/coverage", response_model=PreviewCoverageResponse)
def preview_coverage() -> PreviewCoverageResponse:
    engine = get_engine()
    with Session(engine) as session:
        summary = _previews.coverage_summary(session)
    return PreviewCoverageResponse(**summary)
