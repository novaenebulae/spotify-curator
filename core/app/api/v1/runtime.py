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
        "app_env": settings.app_env,
        "run_env": settings.run_env,
        "essentia_model_profile": settings.effective_essentia_model_profile,
        "essentia_tf_warmup": settings.essentia_tf_warmup,
        "essentia_tf_device": settings.essentia_tf_device,
        "essentia_tf_batch_size": settings.effective_essentia_tf_batch_size,
        "essentia_tensorflow_workers": settings.essentia_tensorflow_workers,
        "audio_segment_max_seconds": settings.audio_segment_max_seconds,
        "audio_keep_segments_after_analysis": settings.audio_keep_segments_after_analysis,
        "audio_segment_default_seconds": settings.audio_segment_default_seconds,
        "worker_heartbeats_enabled": settings.worker_heartbeats_enabled,
        "essentia_lowlevel_pipeline_version": settings.essentia_lowlevel_pipeline_version,
        "audio_segment_strategy": settings.audio_segment_strategy,
        "audio_previews_enabled": settings.audio_previews_enabled,
        "deezer_preview_ui_min_confidence": settings.deezer_preview_ui_min_confidence,
        "deezer_preview_analysis_min_confidence": settings.deezer_preview_analysis_min_confidence,
        "youtube_min_confidence": settings.youtube_min_confidence,
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
