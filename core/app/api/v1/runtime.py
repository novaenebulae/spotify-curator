from __future__ import annotations

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

from app.jobs.service import JobService
from app.observability.diagnostics import (
    list_recent_checks,
    persist_checks,
    run_docker_checks,
)
from app.settings.config import settings

router = APIRouter(prefix="/runtime")
_jobs = JobService()


@router.get("/config")
def runtime_config() -> dict:
    return {
        "api_base_url": f"http://{settings.core_host}:{settings.core_port}{settings.api_v1_prefix}",
        "database_configured": bool(settings.database_url),
        "spotify_client_id_configured": bool(settings.spotify_client_id),
        "export_dir": settings.export_dir,
        "cache_dir": settings.cache_dir,
        "data_dir": settings.data_dir,
        "app_version": settings.app_version,
    }


@router.get("/docker/checks")
def docker_checks_list() -> dict:
    return {"items": list_recent_checks(limit=50)}


@router.post("/docker/checks/run")
def docker_checks_run() -> dict:
    job_id = _jobs.create("docker_runtime_checks")
    logger.info("Docker runtime checks job created: %s", job_id)

    def _run() -> dict:
        results = run_docker_checks()
        items = persist_checks(results)
        logger.info("Docker runtime checks job %s finished (%d checks)", job_id, len(items))
        return {"checks_run": len(items), "items": items}

    _jobs.start_background(job_id, _run)
    return {"job_id": job_id, "status": "pending"}
