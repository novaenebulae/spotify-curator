from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_jobs import Job
from app.jobs.status_mapping import map_job_status

INSIGHT_JOB_TYPES = (
    "reccobeats_enrichment",
    "audio_download",
    "essentia_lowlevel_analysis",
    "preview_resolve",
    "audio_analysis_pipeline",
)

_TERMINAL_DB = ("succeeded", "failed", "cancelled", "partial")


def latest_jobs_by_type(session: Session) -> dict[str, dict | None]:
    out: dict[str, dict | None] = {t: None for t in INSIGHT_JOB_TYPES}
    for job_type in INSIGHT_JOB_TYPES:
        row = session.execute(
            select(Job)
            .where(
                Job.job_type == job_type,
                Job.status.in_(_TERMINAL_DB),
                Job.finished_at.is_not(None),
            )
            .order_by(Job.finished_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            continue
        result: dict = {}
        try:
            result = json.loads(row.result_json or "{}")
        except json.JSONDecodeError:
            result = {}
        out[job_type] = {
            "id": row.id,
            "job_type": row.job_type,
            "status": map_job_status(row.status),
            "progress_current": row.progress_current,
            "progress_total": row.progress_total,
            "current_step": row.current_step,
            "last_error": row.last_error or None,
            "result": result,
            "result_json": result,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        }
    return out
