from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.track_selection import AudioTrackSelectionService
from app.database.engine import get_engine
from app.database.models_jobs import Job
from app.jobs.items.constants import ITEM_TYPE_ESSENTIA_LOWLEVEL_TRACK, JOB_TYPE_ESSENTIA_LOWLEVEL
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService
from app.observability.errors import ApiError


class EssentiaLowlevelJobService:
    def __init__(
        self,
        *,
        jobs: JobService | None = None,
        items: JobItemService | None = None,
        selection: AudioTrackSelectionService | None = None,
    ) -> None:
        self._jobs = jobs or JobService()
        self._items = items or JobItemService()
        self._selection = selection or AudioTrackSelectionService()

    def start_analysis_job(
        self,
        *,
        track_ids: list[int] | None = None,
        filter_dict: dict[str, Any] | None = None,
        only_missing: bool = True,
        retry_failed: bool = False,
        force_refresh: bool = False,
        limit: int | None = None,
        cleanup_after: bool = True,
        require_existing_segments: bool = True,
    ) -> str:
        engine = get_engine()
        with Session(engine) as session:
            if self._has_running_analysis_job(session):
                raise ApiError(
                    code="JOB_ALREADY_RUNNING",
                    message="An Essentia low-level analysis job is already queued or running",
                    status_code=409,
                )
            ids = self._selection.resolve_for_analysis(
                session,
                track_ids=track_ids,
                filter_dict=filter_dict,
                only_missing=only_missing,
                retry_failed=retry_failed,
                force_refresh=force_refresh,
                limit=limit,
                require_existing_segments=require_existing_segments,
            )
            if not ids:
                if require_existing_segments:
                    hint = (
                        "No eligible tracks for local analysis. Download 30s segments first "
                        "(use « Download then analyze »), or disable « Only missing » if tracks "
                        "already have segments but need re-analysis."
                    )
                else:
                    hint = "No tracks matched the analysis criteria."
                raise ApiError(
                    code="NO_TRACKS",
                    message=hint,
                    status_code=400,
                    details={
                        "reason": "no_segments" if require_existing_segments else "no_eligible_tracks",
                        "require_existing_segments": require_existing_segments,
                    },
                )

        job_id = self._jobs.create(JOB_TYPE_ESSENTIA_LOWLEVEL)
        input_payload = {
            "cleanup_after": cleanup_after,
            "require_existing_segments": require_existing_segments,
            "force_refresh": force_refresh,
        }
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job:
                job.progress_total = len(ids)
                job.progress_current = 0
                job.current_step = "queued"
                job.result_json = json.dumps({"track_count": len(ids)})
            self._items.create_items_for_job(
                session,
                job_id=job_id,
                item_type=ITEM_TYPE_ESSENTIA_LOWLEVEL_TRACK,
                track_ids=ids,
                input_payload=input_payload,
                max_attempts=3,
            )
            session.commit()
        return job_id

    def _has_running_analysis_job(self, session: Session) -> bool:
        row = session.execute(
            select(Job.id).where(
                Job.job_type == JOB_TYPE_ESSENTIA_LOWLEVEL,
                Job.status.in_(("queued", "running")),
            )
        ).first()
        return row is not None
