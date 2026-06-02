from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_jobs import Job
from app.database.repositories.track_previews import TrackPreviewsRepository
from app.jobs.items.constants import ITEM_TYPE_PREVIEW_RESOLVE_TRACK, JOB_TYPE_PREVIEW_RESOLVE
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService
from app.observability.errors import ApiError


class PreviewResolveJobService:
    def __init__(
        self,
        *,
        jobs: JobService | None = None,
        items: JobItemService | None = None,
        previews: TrackPreviewsRepository | None = None,
    ) -> None:
        self._jobs = jobs or JobService()
        self._items = items or JobItemService()
        self._previews = previews or TrackPreviewsRepository()

    def start_resolve_job(
        self,
        *,
        only_missing: bool = True,
        force_refresh: bool = False,
        limit: int | None = None,
    ) -> str:
        engine = get_engine()
        with Session(engine) as session:
            if self._has_running(session):
                raise ApiError(
                    code="JOB_ALREADY_RUNNING",
                    message="A preview resolve job is already queued or running",
                    status_code=409,
                )
            ids = self._select_track_ids(
                session,
                only_missing=only_missing and not force_refresh,
                limit=limit,
            )
            if not ids:
                raise ApiError(
                    code="NO_TRACKS",
                    message="No tracks matched preview resolve criteria",
                    status_code=400,
                )

        job_id = self._jobs.create(JOB_TYPE_PREVIEW_RESOLVE)
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
                item_type=ITEM_TYPE_PREVIEW_RESOLVE_TRACK,
                track_ids=ids,
                input_payload={"provider": "deezer", "force_refresh": force_refresh},
                max_attempts=3,
            )
            session.commit()
        return job_id

    def _select_track_ids(
        self,
        session: Session,
        *,
        only_missing: bool,
        limit: int | None,
    ) -> list[int]:
        if only_missing:
            return self._previews.list_track_ids_missing(
                session, provider="deezer", limit=limit
            )
        from app.database.models_library import Track

        stmt = select(Track.id).order_by(Track.id)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(session.scalars(stmt))

    def _has_running(self, session: Session) -> bool:
        row = session.execute(
            select(Job.id).where(
                Job.job_type == JOB_TYPE_PREVIEW_RESOLVE,
                Job.status.in_(("queued", "running")),
            )
        ).first()
        return row is not None
