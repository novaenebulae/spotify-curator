from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.jobs.service import JobService

router = APIRouter(prefix="/jobs")
_jobs = JobService()


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.__dict__

