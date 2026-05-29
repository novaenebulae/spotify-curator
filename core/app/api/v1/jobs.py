from __future__ import annotations

from fastapi import APIRouter

from app.jobs.service import JobService
from app.observability.errors import ApiError

router = APIRouter(prefix="/jobs")
_jobs = JobService()


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise ApiError(code="NOT_FOUND", message="Job not found.", status_code=404)
    return job.to_api_dict()
