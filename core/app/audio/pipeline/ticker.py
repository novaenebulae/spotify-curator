from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.pipeline.audio_cleanup import PipelineAudioCleanupService
from app.audio.pipeline.constants import JOB_TYPE_AUDIO_ANALYSIS_PIPELINE
from app.audio.pipeline.feature_aggregation import PipelineFeatureAggregationService
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator
from app.database.engine import get_engine
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

        for job_id in job_ids:
            deps_unblocked += self._orchestrator.refresh_dependencies(job_id)
            agg_ran += self._aggregation.try_run_pending_for_job(job_id)
            cleanup_ran += self._cleanup.try_run_pending_for_job(job_id)
            with Session(engine) as session:
                self._items.recompute_job_progress(session, job_id)
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
