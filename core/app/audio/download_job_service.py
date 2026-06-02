from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.audio.track_selection import AudioTrackSelectionService
from app.database.engine import get_engine
from app.database.models_jobs import Job
from app.jobs.items.constants import ITEM_TYPE_AUDIO_DOWNLOAD_TRACK, JOB_TYPE_AUDIO_DOWNLOAD
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService
from app.observability.errors import ApiError


class AudioDownloadJobService:
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

    def start_download_job(
        self,
        *,
        track_ids: list[int] | None = None,
        filter_dict: dict[str, Any] | None = None,
        strategy: str = "abc_default",
        segment_duration_seconds: float | None = None,
        only_missing: bool = True,
        retry_failed: bool = False,
        limit: int | None = None,
        provider: str = "ytdlp",
    ) -> str:
        engine = get_engine()
        with Session(engine) as session:
            if self._has_running_download_job(session):
                raise ApiError(
                    code="JOB_ALREADY_RUNNING",
                    message="An audio download job is already queued or running",
                    status_code=409,
                )
            ids = self._selection.resolve_for_download(
                session,
                track_ids=track_ids,
                filter_dict=filter_dict,
                only_missing=only_missing,
                retry_failed=retry_failed,
                limit=limit,
            )
            if not ids:
                hint = (
                    "All candidate tracks already have downloaded segments. "
                    "Run with only_missing=false to re-download, or pick tracks without segments."
                    if only_missing and not retry_failed
                    else "No tracks matched the download criteria."
                )
                raise ApiError(
                    code="NO_TRACKS",
                    message=hint,
                    status_code=400,
                    details={"reason": "no_eligible_tracks", "only_missing": only_missing},
                )

        job_id = self._jobs.create(JOB_TYPE_AUDIO_DOWNLOAD)
        input_payload = {
            "strategy": strategy,
            "segment_duration_seconds": segment_duration_seconds,
            "provider": provider,
        }
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job:
                job.progress_total = len(ids)
                job.progress_current = 0
                job.current_step = "queued"
                job.result_json = json.dumps({"track_count": len(ids), "provider": provider})
            self._items.create_items_for_job(
                session,
                job_id=job_id,
                item_type=ITEM_TYPE_AUDIO_DOWNLOAD_TRACK,
                track_ids=ids,
                input_payload=input_payload,
                max_attempts=3,
            )
            session.commit()
        return job_id

    def _has_running_download_job(self, session: Session) -> bool:
        from sqlalchemy import select

        row = session.execute(
            select(Job.id).where(
                Job.job_type == JOB_TYPE_AUDIO_DOWNLOAD,
                Job.status.in_(("queued", "running")),
            )
        ).first()
        return row is not None
