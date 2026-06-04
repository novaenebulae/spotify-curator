from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_jobs import Job as JobRow
from app.jobs.insights import latest_jobs_by_type
from app.audio.pipeline.constants import ALL_PIPELINE_STAGES, JOB_TYPE_AUDIO_ANALYSIS_PIPELINE, STAGE_STATUSES
from app.jobs.items.constants import WORKER_MANAGED_JOB_TYPES
from app.jobs.items.events import JobEventsService
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService
from app.jobs.status_mapping import map_job_status
from app.observability.errors import ApiError

router = APIRouter(prefix="/jobs")
_jobs = JobService()
_items = JobItemService()
_events = JobEventsService()

@router.get("")
def list_jobs(
    job_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    engine = get_engine()
    with Session(engine) as session:
        stmt = select(JobRow).order_by(JobRow.created_at.desc()).limit(limit)
        if job_type:
            stmt = stmt.where(JobRow.job_type == job_type)
        if status:
            stmt = stmt.where(JobRow.status == status)
        rows = list(session.scalars(stmt))
    return {
        "jobs": [
            {
                "id": r.id,
                "job_type": r.job_type,
                "status": map_job_status(r.status),
                "progress_current": r.progress_current,
                "progress_total": r.progress_total,
                "current_step": r.current_step,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/insights/latest")
def get_latest_job_insights() -> dict:
    engine = get_engine()
    with Session(engine) as session:
        jobs = latest_jobs_by_type(session)
    return {"jobs": jobs}


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise ApiError(code="NOT_FOUND", message="Job not found.", status_code=404)
    payload = job.to_api_dict()
    if job.job_type == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE:
        stage_counts = _items.pipeline_stage_counts(job_id)
        payload["stages"] = {
            stage: {status: stage_counts.get(stage, {}).get(status, 0) for status in STAGE_STATUSES}
            for stage in ALL_PIPELINE_STAGES
        }
        payload["tracks_progress"] = _items.pipeline_track_progress(job_id)
    return payload


@router.get("/{job_id}/events")
def list_job_events(
    job_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None),
) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise ApiError(code="NOT_FOUND", message="Job not found.", status_code=404)
    events = _events.list_events(
        job_id, limit=limit, offset=offset, event_type=event_type
    )
    return {"job_id": job_id, "events": events, "count": len(events)}


@router.get("/{job_id}/items")
def list_job_items(
    job_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise ApiError(code="NOT_FOUND", message="Job not found.", status_code=404)
    items = _items.list_items(job_id, limit=limit, offset=offset)
    return {"job_id": job_id, "items": items, "count": len(items)}


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise ApiError(code="NOT_FOUND", message="Job not found.", status_code=404)
    if job.status not in ("queued", "running"):
        raise ApiError(
            code="JOB_NOT_CANCELLABLE",
            message=f"Job is not running (status={job.status}).",
            status_code=409,
        )
    if job.job_type in WORKER_MANAGED_JOB_TYPES:
        _items.cancel_pending_for_job(job_id)
    elif not _jobs.request_cancel(job_id):
        engine = get_engine()
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        with Session(engine) as session:
            row = session.get(JobRow, job_id)
            if row is not None:
                row.status = "cancelled"
                row.finished_at = now
                row.current_step = "cancelled"
                row.last_error = "Cancelled by user (no active worker)"
                session.commit()
    return {"job_id": job_id, "status": map_job_status("cancelled")}
