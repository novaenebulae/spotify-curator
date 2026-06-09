from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_AUDIO_CLEANUP,
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_FEATURE_AGGREGATION,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.consumers import consumer_group_for_segment
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.database.repositories.job_items import JobItemsRepository
from app.jobs.items.events import JobEventsService
from app.settings.config import settings


def _segment_index_from_item(item: JobItem) -> int | None:
    try:
        payload = json.loads(item.input_json or "{}")
    except json.JSONDecodeError:
        return None
    idx = payload.get("segment_index")
    return int(idx) if idx is not None else None


class PipelineSegmentHandoffService:
    def __init__(
        self,
        *,
        orchestrator: AnalysisPipelineOrchestrator | None = None,
        events: JobEventsService | None = None,
    ) -> None:
        self._orchestrator = orchestrator or AnalysisPipelineOrchestrator()
        self._events = events or JobEventsService()
        self._items = JobItemsRepository()

    def on_segment_ready(
        self,
        session: Session,
        *,
        job_id: str,
        track_id: int,
        segment_id: int,
        download_item_id: str,
        segment_index: int | None = None,
    ) -> int:
        """Bind DB segment id to pipeline stages and unblock analysis consumers."""
        job = session.get(Job, job_id)
        if job is None or job.job_type != JOB_TYPE_AUDIO_ANALYSIS_PIPELINE:
            return 0

        download_item = session.get(JobItem, download_item_id)
        if download_item is None:
            return 0

        group = consumer_group_for_segment(segment_id)
        updated = self._bind_segment_to_slot(
            session,
            job_id=job_id,
            track_id=track_id,
            segment_id=segment_id,
            segment_index=segment_index
            if segment_index is not None
            else _segment_index_from_item(download_item),
            consumer_group=group,
            download_item_id=download_item_id,
        )

        self._events.append(
            session,
            job_id=job_id,
            item_id=download_item_id,
            event_type="segment_ready",
            message=f"Segment {segment_id} ready for analysis",
            context={
                "track_id": track_id,
                "segment_id": segment_id,
                "consumer_group": group,
                "stages_updated": updated,
            },
        )
        session.flush()
        return updated

    def complete_segment_handoff(self, job_id: str) -> int:
        """Refresh blocked stages after the caller has committed segment binding."""
        stages = (
            STAGE_ESSENTIA_LOWLEVEL,
            STAGE_ESSENTIA_TENSORFLOW,
            STAGE_FEATURE_AGGREGATION,
            STAGE_AUDIO_CLEANUP,
        )
        unblocked = 0
        for stage in stages:
            unblocked += self._orchestrator.refresh_dependencies(
                job_id,
                stage_names=(stage,),
                limit=500,
            )
        return unblocked

    def _bind_segment_to_slot(
        self,
        session: Session,
        *,
        job_id: str,
        track_id: int,
        segment_id: int,
        segment_index: int | None,
        consumer_group: str,
        download_item_id: str,
    ) -> int:
        items = list(
            session.scalars(
                select(JobItem).where(
                    JobItem.job_id == job_id,
                    JobItem.track_id == track_id,
                    JobItem.stage_name.is_not(None),
                )
            )
        )
        download_ids = {download_item_id}
        for item in items:
            if item.depends_on_item_id:
                download_ids.add(item.depends_on_item_id)

        updated = 0
        for item in items:
            if not self._item_in_segment_slot(
                item,
                download_item_id=download_item_id,
                segment_index=segment_index,
                download_ids=download_ids,
            ):
                continue
            self._items.update_fields(
                session,
                item.id,
                segment_id=segment_id,
                consumer_group=consumer_group,
            )
            updated += 1
        session.flush()
        return updated

    @staticmethod
    def _item_in_segment_slot(
        item: JobItem,
        *,
        download_item_id: str,
        segment_index: int | None,
        download_ids: set[str],
    ) -> bool:
        if item.id == download_item_id or item.depends_on_item_id in download_ids:
            return True
        if segment_index is None:
            return False
        return _segment_index_from_item(item) == segment_index


def is_streaming_pipeline_enabled() -> bool:
    return settings.analysis_pipeline_mode == "streaming"
