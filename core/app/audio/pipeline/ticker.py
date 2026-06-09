from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audio.pipeline.audio_cleanup import PipelineAudioCleanupService
from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_AUDIO_CLEANUP,
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_FEATURE_AGGREGATION,
)
from app.audio.pipeline.feature_aggregation import PipelineFeatureAggregationService
from app.settings.config import settings
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator
from app.database.engine import get_engine
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.jobs.items.service import JobItemService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineTickResult:
    jobs_ticked: int
    stale_locks_released: int
    dependencies_unblocked: int
    aggregation_ran: int
    cleanup_ran: int
    jobs_finished: list[str]


class AnalysisPipelineTicker:
    """Periodic driver for core-only pipeline stages (aggregation, cleanup)."""

    def __init__(
        self,
        *,
        items: JobItemService | None = None,
        orchestrator: AnalysisPipelineOrchestrator | None = None,
        aggregation: PipelineFeatureAggregationService | None = None,
        cleanup: PipelineAudioCleanupService | None = None,
    ) -> None:
        self._items = items or JobItemService()
        self._orchestrator = orchestrator or AnalysisPipelineOrchestrator(items=self._items)
        self._aggregation = aggregation or PipelineFeatureAggregationService(items=self._items)
        self._cleanup = cleanup or PipelineAudioCleanupService(items=self._items)
        self._tick_count = 0

    def tick_running_jobs(self) -> PipelineTickResult:
        stale_locks = self._items.release_stale_pipeline_stage_locks()

        engine = get_engine()
        with Session(engine) as session:
            job_ids = list(
                session.scalars(
                    select(Job.id).where(
                        Job.job_type == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
                        Job.status.in_(("queued", "running")),
                    )
                )
            )

        deps_unblocked = 0
        agg_ran = 0
        cleanup_ran = 0
        finished: list[str] = []
        self._tick_count += 1
        include_track_progress = (
            self._tick_count % max(1, settings.analysis_pipeline_tick_progress_every_n) == 0
        )
        downstream_stages = (
            STAGE_ESSENTIA_LOWLEVEL,
            STAGE_ESSENTIA_TENSORFLOW,
            STAGE_FEATURE_AGGREGATION,
            STAGE_AUDIO_CLEANUP,
        )

        for job_id in job_ids:
            for stage in downstream_stages:
                deps_unblocked += self._orchestrator.refresh_dependencies(
                    job_id,
                    stage_names=(stage,),
                    limit=settings.analysis_pipeline_refresh_batch_size,
                )
            agg_batches = self._agg_batches_for_job(job_id)
            for _ in range(agg_batches):
                ran = self._aggregation.try_run_pending_for_job(job_id)
                agg_ran += ran
                if ran == 0:
                    break
            cleanup_ran += self._cleanup.try_run_pending_for_job(job_id)
            if agg_ran or cleanup_ran or deps_unblocked or include_track_progress:
                with Session(engine) as session:
                    self._items.recompute_job_progress(
                        session,
                        job_id,
                        include_track_progress=include_track_progress,
                    )
                    session.commit()
                job = session.get(Job, job_id)
                if job is not None and job.status not in ("queued", "running"):
                    finished.append(job_id)

        if stale_locks or deps_unblocked or agg_ran or cleanup_ran or finished:
            logger.info(
                "pipeline_tick jobs=%d stale_locks=%d unblocked=%d agg=%d cleanup=%d finished=%s",
                len(job_ids),
                stale_locks,
                deps_unblocked,
                agg_ran,
                cleanup_ran,
                finished,
            )

        return PipelineTickResult(
            jobs_ticked=len(job_ids),
            stale_locks_released=stale_locks,
            dependencies_unblocked=deps_unblocked,
            aggregation_ran=agg_ran,
            cleanup_ran=cleanup_ran,
            jobs_finished=finished,
        )

    def _agg_pending_count(self, job_id: str) -> int:
        engine = get_engine()
        with Session(engine) as session:
            count = session.scalar(
                select(func.count())
                .select_from(JobItem)
                .where(
                    JobItem.job_id == job_id,
                    JobItem.stage_name == STAGE_FEATURE_AGGREGATION,
                    JobItem.status == "pending",
                )
            )
            return int(count or 0)

    def _agg_backlog_high(self, job_id: str) -> bool:
        threshold = max(1, settings.analysis_pipeline_agg_priority_backlog)
        return self._agg_pending_count(job_id) >= threshold

    def _agg_batches_for_job(self, job_id: str) -> int:
        if not self._agg_backlog_high(job_id):
            return 1
        return max(1, settings.analysis_pipeline_agg_priority_batches)
