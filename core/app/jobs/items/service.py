from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text, update
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.database.repositories.job_items import JobItemsRepository
from app.audio.pipeline.constants import (
    ALL_PIPELINE_STAGES,
    ITEM_TYPE_ANALYSIS_PIPELINE_STAGE,
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    PIPELINE_MODE_STREAMING,
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
    STAGE_SEGMENT_DOWNLOAD,
    STAGE_STATUSES,
)
from app.jobs.items.constants import (
    JOB_TYPE_PREVIEW_RESOLVE,
    TERMINAL_ITEM_STATUSES,
    WORKER_ITEM_TYPES,
    WORKER_TYPE_AUDIO_DOWNLOADER,
    WORKER_TYPE_ESSENTIA_LOWLEVEL,
    WORKER_TYPE_ESSENTIA_TENSORFLOW,
)
from app.jobs.items.events import JobEventsService
from app.jobs.service import JobService
from app.settings.config import settings


@dataclass(frozen=True)
class ReservedJobItem:
    id: str
    job_id: str
    item_type: str
    track_id: int | None
    segment_id: int | None
    input_json: dict[str, Any]
    attempt_count: int


class JobItemService:
    def __init__(
        self,
        *,
        items_repo: JobItemsRepository | None = None,
        jobs: JobService | None = None,
        events: JobEventsService | None = None,
    ) -> None:
        self._items = items_repo or JobItemsRepository()
        self._jobs = jobs or JobService()
        self._events = events or JobEventsService()

    def lock_timeout_for_worker(self, worker_type: str) -> int:
        if worker_type == "audio_downloader":
            return settings.audio_download_item_lock_timeout_seconds
        if worker_type == "essentia_lowlevel":
            return settings.essentia_lowlevel_item_lock_timeout_seconds
        if worker_type == WORKER_TYPE_ESSENTIA_TENSORFLOW:
            return settings.essentia_tensorflow_item_lock_timeout_seconds
        return settings.job_item_lock_timeout_seconds

    def create_items_for_job(
        self,
        session: Session,
        *,
        job_id: str,
        item_type: str,
        track_ids: list[int],
        input_payload: dict[str, Any] | None = None,
        max_attempts: int | None = None,
    ) -> list[str]:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        payload = json.dumps(input_payload or {})
        attempts = max_attempts or settings.job_default_max_attempts
        ids: list[str] = []
        rows: list[JobItem] = []
        for track_id in track_ids:
            item_id = uuid.uuid4().hex
            ids.append(item_id)
            rows.append(
                JobItem(
                    id=item_id,
                    job_id=job_id,
                    item_type=item_type,
                    track_id=track_id,
                    segment_id=None,
                    status="pending",
                    priority=0,
                    attempt_count=0,
                    max_attempts=attempts,
                    locked_by=None,
                    locked_at=None,
                    next_retry_at=None,
                    error_code=None,
                    error_message=None,
                    input_json=payload,
                    result_json="{}",
                    created_at=now,
                    started_at=None,
                    finished_at=None,
                )
            )
        self._items.bulk_insert(session, rows)
        session.flush()
        return ids

    def create_pipeline_stage_item(
        self,
        session: Session,
        *,
        job_id: str,
        track_id: int,
        stage_name: str,
        segment_id: int | None = None,
        depends_on_item_id: str | None = None,
        consumer_group: str | None = None,
        model_name: str | None = None,
        pipeline_version: str | None = None,
        input_payload: dict[str, Any] | None = None,
        status: str = "pending",
        blocked_reason: str | None = None,
        max_attempts: int | None = None,
    ) -> str:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        item_id = uuid.uuid4().hex
        attempts = max_attempts or settings.job_default_max_attempts
        row = JobItem(
            id=item_id,
            job_id=job_id,
            item_type=ITEM_TYPE_ANALYSIS_PIPELINE_STAGE,
            track_id=track_id,
            segment_id=segment_id,
            stage_name=stage_name,
            depends_on_item_id=depends_on_item_id,
            consumer_group=consumer_group,
            model_name=model_name,
            pipeline_version=pipeline_version,
            blocked_reason=blocked_reason,
            status=status,
            priority=0,
            attempt_count=0,
            max_attempts=attempts,
            locked_by=None,
            locked_at=None,
            next_retry_at=None,
            error_code=None,
            error_message=None,
            input_json=json.dumps(input_payload or {}),
            result_json="{}",
            created_at=now,
            started_at=None,
            finished_at=None,
        )
        self._items.insert(session, row)
        return item_id

    def reserve_next(
        self,
        *,
        worker_id: str,
        worker_type: str,
    ) -> ReservedJobItem | None:
        if settings.analysis_pipeline_mode == PIPELINE_MODE_STREAMING:
            if worker_type == WORKER_TYPE_AUDIO_DOWNLOADER:
                pipeline_item = self._reserve_pipeline_stage_item(
                    worker_id=worker_id,
                    lock_timeout=self.lock_timeout_for_worker(worker_type),
                    stage_name=STAGE_SEGMENT_DOWNLOAD,
                )
                if pipeline_item is not None:
                    return pipeline_item
            if worker_type == WORKER_TYPE_ESSENTIA_LOWLEVEL:
                pipeline_item = self._reserve_pipeline_stage_item(
                    worker_id=worker_id,
                    lock_timeout=self.lock_timeout_for_worker(worker_type),
                    stage_name=STAGE_ESSENTIA_LOWLEVEL,
                )
                if pipeline_item is not None:
                    return pipeline_item
            if worker_type == WORKER_TYPE_ESSENTIA_TENSORFLOW:
                for stage_name in (
                    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
                    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
                ):
                    pipeline_item = self._reserve_pipeline_stage_item(
                        worker_id=worker_id,
                        lock_timeout=self.lock_timeout_for_worker(worker_type),
                        stage_name=stage_name,
                    )
                    if pipeline_item is not None:
                        return pipeline_item

        item_types = WORKER_ITEM_TYPES.get(worker_type, ())
        if not item_types:
            return None
        lock_timeout = self.lock_timeout_for_worker(worker_type)
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        stale_before = now - timedelta(seconds=lock_timeout)
        engine = get_engine()

        with Session(engine) as session:
            conn = session.connection()
            conn.execute(text("BEGIN IMMEDIATE"))
            try:
                placeholders = ", ".join(f":t{i}" for i in range(len(item_types)))
                params: dict[str, Any] = {
                    "now": now,
                    "stale_before": stale_before,
                    "worker_id": worker_id,
                }
                for i, it in enumerate(item_types):
                    params[f"t{i}"] = it

                row = conn.execute(
                    text(
                        f"""
                        SELECT i.id, i.job_id, i.item_type, i.track_id, i.segment_id,
                               i.input_json, i.attempt_count
                        FROM job_items i
                        INNER JOIN jobs j ON j.id = i.job_id
                        WHERE i.status IN ('pending', 'rate_limited')
                          AND i.item_type IN ({placeholders})
                          AND j.status IN ('queued', 'running')
                          AND (i.next_retry_at IS NULL OR i.next_retry_at <= :now)
                          AND (i.locked_by IS NULL OR i.locked_at < :stale_before)
                        ORDER BY i.priority DESC, i.created_at ASC
                        LIMIT 1
                        """
                    ),
                    params,
                ).fetchone()

                if row is None:
                    conn.execute(text("COMMIT"))
                    return None

                item_id = row[0]
                updated = conn.execute(
                    text(
                        """
                        UPDATE job_items
                        SET status = 'running',
                            locked_by = :worker_id,
                            locked_at = :now,
                            started_at = COALESCE(started_at, :now),
                            attempt_count = attempt_count + 1
                        WHERE id = :item_id
                          AND (locked_by IS NULL OR locked_at < :stale_before)
                        """
                    ),
                    {"worker_id": worker_id, "now": now, "item_id": item_id, "stale_before": stale_before},
                )
                if updated.rowcount != 1:
                    conn.execute(text("COMMIT"))
                    return None

                job_row = session.get(Job, row[1])
                if job_row and job_row.status in ("queued",):
                    job_row.status = "running"
                    if job_row.started_at is None:
                        job_row.started_at = now

                conn.execute(text("COMMIT"))
                session.commit()
                self.recompute_job_progress(session, row[1])
                session.commit()
            except Exception:
                conn.execute(text("ROLLBACK"))
                raise

        input_json = json.loads(row[5] or "{}")
        return ReservedJobItem(
            id=row[0],
            job_id=row[1],
            item_type=row[2],
            track_id=row[3],
            segment_id=row[4],
            input_json=input_json,
            attempt_count=int(row[6]),
        )

    def _reserve_pipeline_stage_item(
        self,
        *,
        worker_id: str,
        lock_timeout: int,
        stage_name: str,
    ) -> ReservedJobItem | None:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        stale_before = now - timedelta(seconds=lock_timeout)
        engine = get_engine()

        with Session(engine) as session:
            conn = session.connection()
            conn.execute(text("BEGIN IMMEDIATE"))
            try:
                row = conn.execute(
                    text(
                        """
                        SELECT i.id, i.job_id, i.item_type, i.track_id, i.segment_id,
                               i.input_json, i.attempt_count
                        FROM job_items i
                        INNER JOIN jobs j ON j.id = i.job_id
                        WHERE i.status IN ('pending', 'rate_limited')
                          AND i.item_type = :item_type
                          AND i.stage_name = :stage_name
                          AND j.job_type = :job_type
                          AND j.status IN ('queued', 'running')
                          AND (i.next_retry_at IS NULL OR i.next_retry_at <= :now)
                          AND (i.locked_by IS NULL OR i.locked_at < :stale_before)
                        ORDER BY i.priority DESC, i.created_at ASC
                        LIMIT 1
                        """
                    ),
                    {
                        "now": now,
                        "stale_before": stale_before,
                        "worker_id": worker_id,
                        "item_type": ITEM_TYPE_ANALYSIS_PIPELINE_STAGE,
                        "stage_name": stage_name,
                        "job_type": JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
                    },
                ).fetchone()

                if row is None:
                    conn.execute(text("COMMIT"))
                    return None

                item_id = row[0]
                updated = conn.execute(
                    text(
                        """
                        UPDATE job_items
                        SET status = 'running',
                            locked_by = :worker_id,
                            locked_at = :now,
                            started_at = COALESCE(started_at, :now),
                            attempt_count = attempt_count + 1
                        WHERE id = :item_id
                          AND (locked_by IS NULL OR locked_at < :stale_before)
                        """
                    ),
                    {
                        "worker_id": worker_id,
                        "now": now,
                        "item_id": item_id,
                        "stale_before": stale_before,
                    },
                )
                if updated.rowcount != 1:
                    conn.execute(text("COMMIT"))
                    return None

                job_row = session.get(Job, row[1])
                if job_row and job_row.status in ("queued",):
                    job_row.status = "running"
                    if job_row.started_at is None:
                        job_row.started_at = now

                conn.execute(text("COMMIT"))
                session.commit()
                self.recompute_job_progress(session, row[1])
                session.commit()
            except Exception:
                conn.execute(text("ROLLBACK"))
                raise

        input_json = json.loads(row[5] or "{}")
        return ReservedJobItem(
            id=row[0],
            job_id=row[1],
            item_type=row[2],
            track_id=row[3],
            segment_id=row[4],
            input_json=input_json,
            attempt_count=int(row[6]),
        )

    def mark_success(
        self,
        item_id: str,
        *,
        result_json: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        engine = get_engine()
        with Session(engine) as session:
            item = self._items.get(session, item_id)
            if item is None:
                return
            self._items.update_fields(
                session,
                item_id,
                status="success",
                result_json=json.dumps(result_json or {}),
                finished_at=now,
                locked_by=None,
                locked_at=None,
                error_code=None,
                error_message=None,
            )
            self._events.append(
                session,
                job_id=item.job_id,
                item_id=item_id,
                event_type="completed",
                message="Item completed successfully",
            )
            session.commit()
            self.recompute_job_progress(session, item.job_id)
            session.commit()
            self._maybe_refresh_pipeline_dependencies(item.job_id)

    def mark_failed(
        self,
        item_id: str,
        *,
        error_code: str,
        error_message: str,
        retryable: bool = False,
        retry_delay_seconds: int = 60,
    ) -> None:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        engine = get_engine()
        with Session(engine) as session:
            item = self._items.get(session, item_id)
            if item is None:
                return
            status = "failed"
            next_retry = None
            if retryable and item.attempt_count < item.max_attempts:
                status = "rate_limited" if error_code == "RATE_LIMITED" else "pending"
                next_retry = now + timedelta(seconds=retry_delay_seconds)
            self._items.update_fields(
                session,
                item_id,
                status=status,
                error_code=error_code,
                error_message=error_message[:2000],
                finished_at=now if status == "failed" else None,
                locked_by=None,
                locked_at=None,
                next_retry_at=next_retry,
            )
            self._events.append(
                session,
                job_id=item.job_id,
                item_id=item_id,
                event_type="failed",
                level="error",
                message=error_message,
                context={"error_code": error_code},
            )
            session.commit()
            if status == "failed":
                self.recompute_job_progress(session, item.job_id)
                session.commit()

    def mark_skipped(self, item_id: str, *, reason: str) -> None:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        engine = get_engine()
        with Session(engine) as session:
            item = self._items.get(session, item_id)
            if item is None:
                return
            self._items.update_fields(
                session,
                item_id,
                status="skipped",
                error_message=reason[:2000],
                finished_at=now,
                locked_by=None,
                locked_at=None,
            )
            session.commit()
            self.recompute_job_progress(session, item.job_id)
            session.commit()
            self._maybe_refresh_pipeline_dependencies(item.job_id)

    def mark_rate_limited(self, item_id: str, *, retry_after_seconds: int) -> None:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        engine = get_engine()
        with Session(engine) as session:
            item = self._items.get(session, item_id)
            if item is None:
                return
            self._items.update_fields(
                session,
                item_id,
                status="rate_limited",
                next_retry_at=now + timedelta(seconds=retry_after_seconds),
                finished_at=None,
                locked_by=None,
                locked_at=None,
            )
            session.commit()

    def cancel_pending_for_terminal_parent_jobs(self) -> int:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        engine = get_engine()
        with Session(engine) as session:
            count = self._items.cancel_pending_for_terminal_parent_jobs(session, now=now)
            session.commit()
            return count

    def release_stale_locks(self, *, worker_type: str | None = None) -> int:
        lock_timeout = (
            self.lock_timeout_for_worker(worker_type)
            if worker_type
            else settings.job_item_lock_timeout_seconds
        )
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        stale_before = now - timedelta(seconds=lock_timeout)
        engine = get_engine()
        with Session(engine) as session:
            stmt = (
                update(JobItem)
                .where(
                    JobItem.status == "running",
                    JobItem.locked_at.is_not(None),
                    JobItem.locked_at < stale_before,
                )
                .values(status="pending", locked_by=None, locked_at=None)
            )
            if worker_type:
                types = WORKER_ITEM_TYPES.get(worker_type, ())
                if types:
                    stmt = stmt.where(JobItem.item_type.in_(types))
            result = session.execute(stmt)
            session.commit()
            return int(result.rowcount or 0)

    def recompute_job_progress(self, session: Session, job_id: str) -> None:
        counts = self._items.count_by_status(session, job_id)
        total = sum(counts.values())
        terminal = sum(counts.get(s, 0) for s in TERMINAL_ITEM_STATUSES)
        running = counts.get("running", 0)
        job = session.get(Job, job_id)
        if job is None:
            return
        job.progress_total = total
        job.progress_current = terminal
        pending = (
            counts.get("pending", 0) + running + counts.get("rate_limited", 0)
        )
        # blocked items wait on dependencies and are not executable work units
        if pending > 0 and total > 0:
            now = datetime.now(tz=UTC).replace(tzinfo=None)
            if job.status == "queued":
                job.status = "running"
                if job.started_at is None:
                    job.started_at = now
            elif job.status not in ("cancelled",):
                # If work is still pending, the job cannot be terminal.
                job.status = "running"
                job.finished_at = None
            job.current_step = f"processing {terminal}/{total}"
        elif pending == 0 and total > 0:
            self._apply_terminal_job_result(session, job, counts)
        session.flush()

    def _apply_terminal_job_result(
        self, session: Session, job: Job, counts: dict[str, int]
    ) -> None:
        """Aggregate item outcomes into result_json; preserve cancelled status."""
        preserve_cancelled = job.status == "cancelled"
        failed = counts.get("failed", 0)
        success = counts.get("success", 0)
        if not preserve_cancelled:
            if failed > 0 and success > 0:
                job.status = "partial"
            elif failed > 0 and success == 0:
                job.status = "failed"
            else:
                job.status = "succeeded"
        if job.finished_at is None:
            job.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
        if failed > 0 and not job.last_error:
            sample = self._items.first_failed_for_job(session, job.id)
            if sample and sample.error_message:
                job.last_error = sample.error_message[:2000]
        job.result_json = json.dumps(
            self._build_terminal_result_json(session, job, counts)
        )

    def _build_terminal_result_json(
        self,
        session: Session,
        job: Job,
        counts: dict[str, int],
    ) -> dict[str, Any]:
        try:
            existing = json.loads(job.result_json or "{}")
        except json.JSONDecodeError:
            existing = {}
        if not isinstance(existing, dict):
            existing = {}

        failed = counts.get("failed", 0)
        skipped = counts.get("skipped", 0)
        total = sum(counts.values())
        track_count = int(existing.get("track_count") or total or 0)

        if job.job_type == JOB_TYPE_PREVIEW_RESOLVE:
            succeeded, not_found = self._preview_resolve_outcome_counts(session, job.id)
        else:
            succeeded = counts.get("success", 0)
            not_found = 0

        result: dict[str, Any] = {
            **existing,
            "track_count": track_count,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "not_found": not_found,
            "partial": 0,
        }
        if job.job_type == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE:
            stage_counts = self._items.count_by_stage_name(session, job.id)
            result["stages"] = {
                stage: {status: stage_counts.get(stage, {}).get(status, 0) for status in STAGE_STATUSES}
                for stage in ALL_PIPELINE_STAGES
            }
        return result

    def _preview_resolve_outcome_counts(
        self, session: Session, job_id: str
    ) -> tuple[int, int]:
        succeeded = 0
        not_found = 0
        for item in self._items.list_for_job(session, job_id, limit=100_000, offset=0):
            if item.status != "success":
                continue
            try:
                payload = json.loads(item.result_json or "{}")
            except json.JSONDecodeError:
                payload = {}
            if payload.get("is_available"):
                succeeded += 1
            else:
                not_found += 1
        return succeeded, not_found

    def cancel_pending_for_job(self, job_id: str) -> int:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        engine = get_engine()
        with Session(engine) as session:
            count = self._items.cancel_pending_for_job(session, job_id, now=now)
            job = session.get(Job, job_id)
            if job is not None:
                job.status = "cancelled"
                job.finished_at = now
                job.current_step = "cancelled"
                counts = self._items.count_by_status(session, job_id)
                total = sum(counts.values())
                job.progress_total = total
                job.progress_current = sum(
                    counts.get(s, 0) for s in TERMINAL_ITEM_STATUSES
                )
                if total > 0:
                    job.result_json = json.dumps(
                        self._build_terminal_result_json(session, job, counts)
                    )
            session.commit()
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job is not None and job.status == "cancelled":
                counts = self._items.count_by_status(session, job_id)
                pending = (
                    counts.get("pending", 0)
                    + counts.get("running", 0)
                    + counts.get("rate_limited", 0)
                )
                if pending == 0 and sum(counts.values()) > 0:
                    self._apply_terminal_job_result(session, job, counts)
                    session.commit()
        return count

    def list_items(self, job_id: str, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        engine = get_engine()
        with Session(engine) as session:
            rows = self._items.list_for_job(session, job_id, limit=limit, offset=offset)
            return [_item_to_dict(r) for r in rows]

    def is_job_cancelled(self, job_id: str) -> bool:
        return self._jobs.is_cancelled(job_id)

    def _maybe_refresh_pipeline_dependencies(self, job_id: str) -> None:
        engine = get_engine()
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job is None or job.job_type != JOB_TYPE_AUDIO_ANALYSIS_PIPELINE:
                return
        from app.audio.pipeline.feature_aggregation import PipelineFeatureAggregationService
        from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator

        AnalysisPipelineOrchestrator(items=self).refresh_dependencies(job_id)
        PipelineFeatureAggregationService(items=self).try_run_pending_for_job(job_id)


def _item_to_dict(row: JobItem) -> dict[str, Any]:
    return {
        "id": row.id,
        "job_id": row.job_id,
        "item_type": row.item_type,
        "track_id": row.track_id,
        "segment_id": row.segment_id,
        "stage_name": row.stage_name,
        "depends_on_item_id": row.depends_on_item_id,
        "consumer_group": row.consumer_group,
        "pipeline_version": row.pipeline_version,
        "blocked_reason": row.blocked_reason,
        "status": row.status,
        "attempt_count": row.attempt_count,
        "max_attempts": row.max_attempts,
        "error_code": row.error_code,
        "error_message": row.error_message,
        "result": json.loads(row.result_json or "{}"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }
