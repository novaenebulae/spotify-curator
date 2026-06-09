from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.audio.cleanup import AudioCleanupService
from app.audio.pipeline.constants import STAGE_AUDIO_CLEANUP, STAGE_SEGMENT_DOWNLOAD
from app.audio.pipeline.consumers import segment_cleanup_allowed
from app.audio.pipeline.orchestrator import _prerequisites_met
from app.database.engine import get_engine
from app.database.models_job_items import JobItem
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.jobs.items.service import PIPELINE_WORKER_ITEM_KWARGS, JobItemService
from app.settings.config import settings
from app.workers.base_worker import _is_sqlite_locked

_NO_TICKER_STAGE_KWARGS = PIPELINE_WORKER_ITEM_KWARGS


class PipelineAudioCleanupService:
    def __init__(
        self,
        *,
        items: JobItemService | None = None,
        cleanup: AudioCleanupService | None = None,
        segments: TrackSegmentsRepository | None = None,
    ) -> None:
        self._items = items or JobItemService()
        self._cleanup = cleanup or AudioCleanupService()
        self._segments = segments or TrackSegmentsRepository()

    def try_run_pending_for_job(self, job_id: str, *, limit: int | None = None) -> int:
        batch = max(1, limit or settings.analysis_pipeline_cleanup_batch_size)
        processed = 0
        engine = get_engine()
        with Session(engine) as session:
            pending = list(
                session.scalars(
                    select(JobItem)
                    .where(
                        JobItem.job_id == job_id,
                        JobItem.stage_name == STAGE_AUDIO_CLEANUP,
                        JobItem.status == "pending",
                    )
                    .order_by(JobItem.created_at.asc())
                    .limit(batch)
                )
            )
        for item in pending:
            if self._run_cleanup_item_with_retry(item.id):
                processed += 1
        return processed

    def _run_cleanup_item_with_retry(self, item_id: str) -> bool:
        delays = (0.0, 0.5, 1.0, 2.0)
        for delay in delays:
            if delay:
                time.sleep(delay)
            try:
                return self._run_cleanup_item(item_id)
            except OperationalError as exc:
                if not _is_sqlite_locked(exc):
                    raise
        return False

    def _run_cleanup_item(self, item_id: str) -> bool:
        engine = get_engine()
        with Session(engine) as session:
            item = session.get(JobItem, item_id)
            if item is None or item.stage_name != STAGE_AUDIO_CLEANUP:
                return False
            if item.status != "pending":
                return False
            if not _prerequisites_met(session, item):
                return False
            track_id = item.track_id
            job_id = item.job_id
            if track_id is None:
                return False

            if settings.audio_keep_segments_after_analysis:
                result_json = {
                    "skipped": True,
                    "reason": "audio_keep_segments_after_analysis",
                }
                self._items.mark_success(
                    item_id, result_json=result_json, **_NO_TICKER_STAGE_KWARGS
                )
                self._items.emit_cleanup_done(
                    job_id=job_id,
                    item_id=item_id,
                    result=result_json,
                )
                return True

            segment_ids = self._segment_ids_for_job_track(session, job_id, track_id)
            blocked = 0
            for seg_id in segment_ids:
                if not segment_cleanup_allowed(session, segment_id=seg_id):
                    blocked += 1
            if blocked > 0:
                self._items.mark_failed(
                    item_id,
                    error_code="SEGMENT_CONSUMER_PENDING",
                    error_message=f"{blocked} segment(s) still have active consumers",
                    retryable=True,
                    **_NO_TICKER_STAGE_KWARGS,
                )
                return True

        result = self._cleanup.cleanup_files(track_id=track_id, job_id=job_id)
        result_json = {
            "matched_files": result.matched_files,
            "deleted_files": result.deleted_files,
            "freed_bytes": result.freed_bytes,
            "errors": result.errors,
        }
        self._items.mark_success(item_id, result_json=result_json, **_NO_TICKER_STAGE_KWARGS)
        self._items.emit_cleanup_done(
            job_id=job_id,
            item_id=item_id,
            result=result_json,
        )
        return True

    def _segment_ids_for_job_track(
        self, session: Session, job_id: str, track_id: int
    ) -> list[int]:
        ids: list[int] = []
        rows = list(
            session.scalars(
                select(JobItem).where(
                    JobItem.job_id == job_id,
                    JobItem.track_id == track_id,
                    JobItem.stage_name == STAGE_SEGMENT_DOWNLOAD,
                    JobItem.status == "success",
                    JobItem.segment_id.is_not(None),
                )
            )
        )
        for row in rows:
            if row.segment_id is not None:
                ids.append(int(row.segment_id))
        if not ids:
            for seg in self._segments.list_for_track(session, track_id, include_deleted=False):
                if seg.temporary_path and job_id in (seg.temporary_path or ""):
                    ids.append(int(seg.id))
        return ids
