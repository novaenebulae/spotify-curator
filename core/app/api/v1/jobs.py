from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_jobs import Job as JobRow
from app.jobs.service import JobService
from app.jobs.status_mapping import map_job_status
from app.observability.errors import ApiError

router = APIRouter(prefix="/jobs")
_jobs = JobService()


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise ApiError(code="NOT_FOUND", message="Job not found.", status_code=404)
    return job.to_api_dict()


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
    if not _jobs.request_cancel(job_id):
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
