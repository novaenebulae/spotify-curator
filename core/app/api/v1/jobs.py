from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_jobs import Job as JobRow
from app.jobs.insights import latest_jobs_by_type
from app.jobs.items.constants import JOB_TYPE_AUDIO_DOWNLOAD, JOB_TYPE_ESSENTIA_LOWLEVEL
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService
from app.jobs.status_mapping import map_job_status
from app.observability.errors import ApiError

router = APIRouter(prefix="/jobs")
_jobs = JobService()
_items = JobItemService()

_WORKER_JOB_TYPES = {JOB_TYPE_AUDIO_DOWNLOAD, JOB_TYPE_ESSENTIA_LOWLEVEL}


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
    return job.to_api_dict()


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
    if job.job_type in _WORKER_JOB_TYPES:
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
