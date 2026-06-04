from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    BLOCKED_REASON_DEPENDENCY_PENDING,
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    PIPELINE_MODE_STREAMING,
    STAGE_AUDIO_CLEANUP,
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
    STAGE_FEATURE_AGGREGATION,
    STAGE_SEGMENT_DOWNLOAD,
    TERMINAL_FOR_DEPENDENCY,
)
from app.database.engine import get_engine
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService
from app.observability.errors import ApiError
from app.settings.config import settings


@dataclass(frozen=True)
class TrackSegmentPlan:
    track_id: int
    segment_ids: list[int]
    planned_segments: tuple[dict[str, Any], ...] = ()


def _consumer_group(segment_id: int | None) -> str | None:
    if segment_id is None:
        return None
    return f"segment:{segment_id}"


def _dependency_met(item: JobItem | None) -> bool:
    if item is None:
        return False
    return item.status in TERMINAL_FOR_DEPENDENCY


def _pipeline_mode(session: Session, job_id: str) -> str:
    job = session.get(Job, job_id)
    if job is None or not job.result_json:
        return PIPELINE_MODE_STREAMING
    try:
        payload = json.loads(job.result_json)
    except json.JSONDecodeError:
        return PIPELINE_MODE_STREAMING
    return str(payload.get("pipeline_mode", PIPELINE_MODE_STREAMING))


def _streaming_segment_handoff_met(session: Session, item: JobItem) -> bool:
    """Download stage produced a segment file but may still be running (handoff)."""
    if item.depends_on_item_id is None or item.segment_id is None:
        return False
    dep = session.get(JobItem, item.depends_on_item_id)
    if dep is None or dep.stage_name != STAGE_SEGMENT_DOWNLOAD:
        return False
    return dep.segment_id == item.segment_id


def _prerequisites_met(session: Session, item: JobItem) -> bool:
    try:
        payload = json.loads(item.input_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    prerequisite_ids = payload.get("prerequisite_item_ids")
    if isinstance(prerequisite_ids, list) and prerequisite_ids:
        for prereq_id in prerequisite_ids:
            prereq = session.get(JobItem, str(prereq_id))
            if not _dependency_met(prereq):
                return False
        return True
    if item.depends_on_item_id:
        dep = session.get(JobItem, item.depends_on_item_id)
        if _dependency_met(dep):
            return True
        if (
            _pipeline_mode(session, item.job_id) == PIPELINE_MODE_STREAMING
            and _streaming_segment_handoff_met(session, item)
        ):
            return True
        return False
    return True


class AnalysisPipelineOrchestrator:
    def __init__(
        self,
        *,
        jobs: JobService | None = None,
        items: JobItemService | None = None,
    ) -> None:
        self._jobs = jobs or JobService()
        self._items = items or JobItemService()

    def create_pipeline_job(
        self,
        track_plans: list[TrackSegmentPlan],
        *,
        include_lowlevel: bool = True,
        include_tensorflow: bool = True,
        pipeline_mode: str = "streaming",
        input_payload: dict[str, Any] | None = None,
    ) -> str:
        if not track_plans:
            raise ApiError(
                code="NO_TRACKS",
                message="At least one track plan is required",
                status_code=400,
            )

        engine = get_engine()
        with Session(engine) as session:
            if self._has_running_pipeline_job(session):
                raise ApiError(
                    code="JOB_ALREADY_RUNNING",
                    message="An audio analysis pipeline job is already queued or running",
                    status_code=409,
                )

        pipeline_version = settings.audio_analysis_pipeline_version
        job_id = self._jobs.create(JOB_TYPE_AUDIO_ANALYSIS_PIPELINE)
        base_input = dict(input_payload or {})

        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job:
                job.progress_total = 0
                job.progress_current = 0
                job.current_step = "queued"
                job.result_json = json.dumps(
                    {
                        "track_count": len(track_plans),
                        "pipeline_version": pipeline_version,
                        "pipeline_mode": pipeline_mode,
                        **base_input,
                    }
                )

            for plan in track_plans:
                segment_ids = plan.segment_ids if plan.segment_ids else [None]
                analysis_prereq_ids: list[str] = []

                for segment_index, segment_id in enumerate(segment_ids):
                    slot_input: dict[str, Any] = {
                        **base_input,
                        "track_id": plan.track_id,
                        "segment_index": segment_index,
                    }
                    if segment_index < len(plan.planned_segments):
                        slot_input["planned_segment"] = plan.planned_segments[segment_index]
                    download_id = self._items.create_pipeline_stage_item(
                        session,
                        job_id=job_id,
                        track_id=plan.track_id,
                        stage_name=STAGE_SEGMENT_DOWNLOAD,
                        segment_id=segment_id,
                        consumer_group=_consumer_group(segment_id),
                        pipeline_version=pipeline_version,
                        input_payload=slot_input,
                        status="pending",
                    )

                    if include_lowlevel:
                        ll_id = self._items.create_pipeline_stage_item(
                            session,
                            job_id=job_id,
                            track_id=plan.track_id,
                            stage_name=STAGE_ESSENTIA_LOWLEVEL,
                            segment_id=segment_id,
                            depends_on_item_id=download_id,
                            consumer_group=_consumer_group(segment_id),
                            pipeline_version=pipeline_version,
                            status="blocked",
                            blocked_reason=BLOCKED_REASON_DEPENDENCY_PENDING,
                        )
                        analysis_prereq_ids.append(ll_id)

                    embeddings_id: str | None = None
                    if include_tensorflow:
                        embeddings_id = self._items.create_pipeline_stage_item(
                            session,
                            job_id=job_id,
                            track_id=plan.track_id,
                            stage_name=STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
                            segment_id=segment_id,
                            depends_on_item_id=download_id,
                            consumer_group=_consumer_group(segment_id),
                            pipeline_version=pipeline_version,
                            status="blocked",
                            blocked_reason=BLOCKED_REASON_DEPENDENCY_PENDING,
                        )
                        classifiers_id = self._items.create_pipeline_stage_item(
                            session,
                            job_id=job_id,
                            track_id=plan.track_id,
                            stage_name=STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
                            segment_id=segment_id,
                            depends_on_item_id=embeddings_id,
                            consumer_group=_consumer_group(segment_id),
                            pipeline_version=pipeline_version,
                            status="blocked",
                            blocked_reason=BLOCKED_REASON_DEPENDENCY_PENDING,
                        )
                        analysis_prereq_ids.append(classifiers_id)

                aggregation_id = self._items.create_pipeline_stage_item(
                    session,
                    job_id=job_id,
                    track_id=plan.track_id,
                    stage_name=STAGE_FEATURE_AGGREGATION,
                    segment_id=None,
                    pipeline_version=pipeline_version,
                    input_payload={"prerequisite_item_ids": analysis_prereq_ids},
                    status="blocked",
                    blocked_reason=BLOCKED_REASON_DEPENDENCY_PENDING,
                )

                self._items.create_pipeline_stage_item(
                    session,
                    job_id=job_id,
                    track_id=plan.track_id,
                    stage_name=STAGE_AUDIO_CLEANUP,
                    segment_id=None,
                    depends_on_item_id=aggregation_id,
                    pipeline_version=pipeline_version,
                    status="blocked",
                    blocked_reason=BLOCKED_REASON_DEPENDENCY_PENDING,
                )

            session.commit()
            self._items.recompute_job_progress(session, job_id)
            session.commit()

        return job_id

    def refresh_dependencies(self, job_id: str) -> int:
        engine = get_engine()
        unblocked = 0
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job is None or job.job_type != JOB_TYPE_AUDIO_ANALYSIS_PIPELINE:
                return 0

            blocked_items = self._items._items.list_for_job_by_status(
                session, job_id, status="blocked"
            )
            for item in blocked_items:
                if not _prerequisites_met(session, item):
                    continue
                self._items._items.update_fields(
                    session,
                    item.id,
                    status="pending",
                    blocked_reason=None,
                )
                unblocked += 1

            if unblocked:
                session.commit()
                self._items.recompute_job_progress(session, job_id)
                session.commit()
        return unblocked

    def retry_stage_item(self, item_id: str) -> bool:
        engine = get_engine()
        with Session(engine) as session:
            item = self._items._items.get(session, item_id)
            if item is None:
                return False
            if item.status != "failed":
                return False
            if item.attempt_count >= item.max_attempts:
                return False
            self._items._items.update_fields(
                session,
                item_id,
                status="pending",
                error_code=None,
                error_message=None,
                finished_at=None,
                locked_by=None,
                locked_at=None,
                next_retry_at=None,
            )
            job_id = item.job_id
            session.commit()

        self.refresh_dependencies(job_id)
        engine2 = get_engine()
        with Session(engine2) as session:
            self._items.recompute_job_progress(session, job_id)
            session.commit()
        return True

    def _has_running_pipeline_job(self, session: Session) -> bool:
        row = session.execute(
            select(Job.id)
            .where(
                Job.job_type == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
                Job.status.in_(("queued", "running")),
            )
            .limit(1)
        ).first()
        return row is not None
