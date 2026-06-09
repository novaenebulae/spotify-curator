from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, TypeVar

from sqlalchemy import and_, or_, select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database.dialect import begin_exclusive_write, is_postgresql_database
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
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
    STAGE_SEGMENT_DOWNLOAD,
    STAGE_STATUSES,
)
from app.jobs.items.constants import (
    JOB_TYPE_PREVIEW_RESOLVE,
    PIPELINE_STAGES_BY_WORKER,
    TERMINAL_ITEM_STATUSES,
    WORKER_ITEM_TYPES,
    WORKER_TYPE_AUDIO_DOWNLOADER,
    WORKER_TYPE_ESSENTIA_LOWLEVEL,
    WORKER_TYPE_ESSENTIA_TENSORFLOW,
)
from app.jobs.items.events import JobEventsService
from app.jobs.service import JobService
from app.settings.config import settings

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

# Workers defer progress recompute to AnalysisPipelineTicker to avoid SQLite write storms.
PIPELINE_WORKER_PROGRESS_KWARGS: dict[str, bool] = {"recompute_progress": False}
PIPELINE_WORKER_ITEM_KWARGS: dict[str, bool] = {
    **PIPELINE_WORKER_PROGRESS_KWARGS,
    "refresh_pipeline": False,
}


def _is_sqlite_locked(exc: BaseException) -> bool:
    if not isinstance(exc, OperationalError):
        return False
    orig = getattr(exc, "orig", None)
    return orig is not None and "locked" in str(orig).lower()


def _reserve_row_lock_sql() -> str:
    if is_postgresql_database():
        return " FOR UPDATE OF i SKIP LOCKED"
    return ""


def _run_with_sqlite_retry(func: Callable[[], _T], *, attempts: int = 6) -> _T:
    delay = 0.05
    for attempt in range(attempts):
        try:
            return func()
        except OperationalError as exc:
            if not _is_sqlite_locked(exc) or attempt == attempts - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 1.0)


@dataclass(frozen=True)
class ReservedJobItem:
    id: str
    job_id: str
    item_type: str
    track_id: int | None
    segment_id: int | None
    input_json: dict[str, Any]
    attempt_count: int
    stage_name: str | None = None


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
                    STAGE_ESSENTIA_TENSORFLOW,
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
            begin_exclusive_write(conn)
            try:
                placeholders = ", ".join(f":t{i}" for i in range(len(item_types)))
                params: dict[str, Any] = {
                    "now": now,
                    "stale_before": stale_before,
                    "worker_id": worker_id,
                }
                for i, it in enumerate(item_types):
                    params[f"t{i}"] = it
                row_lock = _reserve_row_lock_sql()

                row = conn.execute(
                    text(
                        f"""
                        SELECT i.id, i.job_id, i.item_type, i.track_id, i.segment_id,
                               i.input_json, i.attempt_count, i.stage_name
                        FROM job_items i
                        INNER JOIN jobs j ON j.id = i.job_id
                        WHERE i.status IN ('pending', 'rate_limited')
                          AND i.item_type IN ({placeholders})
                          AND j.status IN ('queued', 'running')
                          AND (i.next_retry_at IS NULL OR i.next_retry_at <= :now)
                          AND (i.locked_by IS NULL OR i.locked_at < :stale_before)
                        ORDER BY i.priority DESC, i.created_at ASC
                        LIMIT 1{row_lock}
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
            stage_name=row[7] if len(row) > 7 else None,
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
            begin_exclusive_write(conn)
            try:
                row_lock = _reserve_row_lock_sql()
                row = conn.execute(
                    text(
                        f"""
                        SELECT i.id, i.job_id, i.item_type, i.track_id, i.segment_id,
                               i.input_json, i.attempt_count, i.stage_name
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
                        LIMIT 1{row_lock}
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
                self._emit_stage_started(
                    job_id=row[1],
                    item_id=row[0],
                    stage_name=stage_name,
                    track_id=row[3],
                    segment_id=row[4],
                )
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
            stage_name=row[7] if len(row) > 7 else stage_name,
        )

    def _reserve_pipeline_stage_items(
        self,
        *,
        worker_id: str,
        lock_timeout: int,
        stage_name: str,
        limit: int,
    ) -> list[ReservedJobItem]:
        if limit <= 0:
            return []
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        stale_before = now - timedelta(seconds=lock_timeout)
        engine = get_engine()
        reserved: list[ReservedJobItem] = []

        with Session(engine) as session:
            conn = session.connection()
            begin_exclusive_write(conn)
            try:
                row_lock = _reserve_row_lock_sql()
                rows = conn.execute(
                    text(
                        f"""
                        SELECT i.id, i.job_id, i.item_type, i.track_id, i.segment_id,
                               i.input_json, i.attempt_count, i.stage_name
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
                        LIMIT :limit{row_lock}
                        """
                    ),
                    {
                        "now": now,
                        "stale_before": stale_before,
                        "item_type": ITEM_TYPE_ANALYSIS_PIPELINE_STAGE,
                        "stage_name": stage_name,
                        "job_type": JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
                        "limit": limit,
                    },
                ).fetchall()

                if not rows:
                    conn.execute(text("COMMIT"))
                    return []

                job_ids_touched: set[str] = set()
                started_events: list[tuple[str, str, str, int | None, int | None]] = []
                for row in rows:
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
                        continue

                    job_row = session.get(Job, row[1])
                    if job_row and job_row.status in ("queued",):
                        job_row.status = "running"
                        if job_row.started_at is None:
                            job_row.started_at = now

                    job_ids_touched.add(row[1])
                    input_json = json.loads(row[5] or "{}")
                    reserved.append(
                        ReservedJobItem(
                            id=row[0],
                            job_id=row[1],
                            item_type=row[2],
                            track_id=row[3],
                            segment_id=row[4],
                            input_json=input_json,
                            attempt_count=int(row[6]),
                            stage_name=row[7] if len(row) > 7 else stage_name,
                        )
                    )
                    started_events.append(
                        (row[1], row[0], stage_name, row[3], row[4])
                    )

                conn.execute(text("COMMIT"))
                session.commit()
                for job_id, item_id, stg, track_id, segment_id in started_events:
                    self._emit_stage_started(
                        job_id=job_id,
                        item_id=item_id,
                        stage_name=stg,
                        track_id=track_id,
                        segment_id=segment_id,
                    )
            except Exception:
                conn.execute(text("ROLLBACK"))
                raise

        return reserved

    def _emit_stage_started(
        self,
        *,
        job_id: str,
        item_id: str,
        stage_name: str,
        track_id: int | None,
        segment_id: int | None,
    ) -> None:
        engine = get_engine()
        with Session(engine) as session:
            self._events.append(
                session,
                job_id=job_id,
                item_id=item_id,
                event_type="stage_started",
                message=f"Stage {stage_name} started",
                context={
                    "stage_name": stage_name,
                    "track_id": track_id,
                    "segment_id": segment_id,
                },
                commit=True,
            )

    def emit_model_missing(
        self,
        *,
        job_id: str,
        item_id: str,
        stage_name: str | None,
        models_missing: list[str],
    ) -> None:
        if not models_missing:
            return
        engine = get_engine()
        with Session(engine) as session:
            self._events.append(
                session,
                job_id=job_id,
                item_id=item_id,
                event_type="model_missing",
                level="warning",
                message="One or more TensorFlow models are missing",
                context={
                    "stage_name": stage_name,
                    "models_missing": models_missing,
                },
                commit=True,
            )

    def emit_cleanup_done(
        self,
        *,
        job_id: str,
        item_id: str,
        result: dict[str, Any],
    ) -> None:
        engine = get_engine()
        with Session(engine) as session:
            self._events.append(
                session,
                job_id=job_id,
                item_id=item_id,
                event_type="cleanup_done",
                message="Audio cleanup finished",
                context={
                    "deleted_files": result.get("deleted_files", 0),
                    "freed_bytes": result.get("freed_bytes", 0),
                    "skipped": result.get("skipped", False),
                    "reason": result.get("reason"),
                },
                commit=True,
            )

    def record_pipeline_stage_created(
        self,
        session: Session,
        *,
        job_id: str,
        track_count: int,
        pipeline_mode: str,
    ) -> None:
        stage_counts = self._items.count_by_stage_name(session, job_id)
        self._events.append(
            session,
            job_id=job_id,
            event_type="stage_created",
            message="Analysis pipeline stages created",
            context={
                "track_count": track_count,
                "pipeline_mode": pipeline_mode,
                "stage_item_counts": stage_counts,
            },
        )

    def reserve_pipeline_stage_batch(
        self,
        *,
        worker_id: str,
        worker_type: str,
        stage_names: tuple[str, ...],
        limit: int,
    ) -> list[ReservedJobItem]:
        if limit <= 0:
            return []
        lock_timeout = self.lock_timeout_for_worker(worker_type)
        reserved: list[ReservedJobItem] = []
        remaining = limit
        for stage_name in stage_names:
            if remaining <= 0:
                break
            batch = self._reserve_pipeline_stage_items(
                worker_id=worker_id,
                lock_timeout=lock_timeout,
                stage_name=stage_name,
                limit=remaining,
            )
            reserved.extend(batch)
            remaining = limit - len(reserved)
        return reserved

    def refresh_pipeline_for_job(self, job_id: str) -> None:
        self._maybe_refresh_pipeline_dependencies(job_id)

    def mark_success(
        self,
        item_id: str,
        *,
        result_json: dict[str, Any] | None = None,
        refresh_pipeline: bool = True,
        recompute_progress: bool = True,
    ) -> None:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        engine = get_engine()
        job_id: str | None = None
        with Session(engine) as session:
            item = self._items.get(session, item_id)
            if item is None:
                return
            job_id = item.job_id
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
            _run_with_sqlite_retry(lambda: session.commit())
        if job_id is None:
            return
        if recompute_progress:
            with Session(engine) as session:
                _run_with_sqlite_retry(
                    lambda: (
                        self.recompute_job_progress(session, job_id),
                        session.commit(),
                    )[1]
                )
        if refresh_pipeline:
            self._maybe_refresh_pipeline_dependencies(job_id)

    def mark_failed(
        self,
        item_id: str,
        *,
        error_code: str,
        error_message: str,
        retryable: bool = False,
        retry_delay_seconds: int = 60,
        recompute_progress: bool = True,
        refresh_pipeline: bool = True,
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
            if item.item_type == ITEM_TYPE_ANALYSIS_PIPELINE_STAGE:
                stage_ctx: dict[str, Any] = {
                    "error_code": error_code,
                    "retryable": retryable,
                }
                if item.stage_name:
                    stage_ctx["stage_name"] = item.stage_name
                if item.track_id is not None:
                    stage_ctx["track_id"] = item.track_id
                self._events.append(
                    session,
                    job_id=item.job_id,
                    item_id=item_id,
                    event_type="stage_failed",
                    level="error",
                    message=error_message,
                    context=stage_ctx,
                )
            job_id = item.job_id
            is_pipeline_stage = item.item_type == ITEM_TYPE_ANALYSIS_PIPELINE_STAGE
            _run_with_sqlite_retry(lambda: session.commit())
            if retryable and is_pipeline_stage and refresh_pipeline:
                self.refresh_pipeline_for_job(job_id)
            if recompute_progress:
                with Session(engine) as session2:
                    _run_with_sqlite_retry(
                        lambda: (
                            self.recompute_job_progress(session2, job_id),
                            session2.commit(),
                        )[1]
                    )

    def mark_skipped(
        self,
        item_id: str,
        *,
        reason: str,
        recompute_progress: bool = True,
        refresh_pipeline: bool = True,
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
                status="skipped",
                error_message=reason[:2000],
                finished_at=now,
                locked_by=None,
                locked_at=None,
            )
            job_id = item.job_id
            _run_with_sqlite_retry(lambda: session.commit())
        if recompute_progress:
            with Session(engine) as session:
                _run_with_sqlite_retry(
                    lambda: (
                        self.recompute_job_progress(session, job_id),
                        session.commit(),
                    )[1]
                )
        if refresh_pipeline:
            self._maybe_refresh_pipeline_dependencies(job_id)

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
                scope = self._stale_lock_scope_for_worker(worker_type)
                if scope is not None:
                    stmt = stmt.where(scope)
            result = session.execute(stmt)
            session.commit()
            return int(result.rowcount or 0)

    @staticmethod
    def _stale_lock_scope_for_worker(worker_type: str):
        legacy_types = WORKER_ITEM_TYPES.get(worker_type, ())
        pipeline_stages = PIPELINE_STAGES_BY_WORKER.get(worker_type, ())
        clauses = []
        if legacy_types:
            clauses.append(JobItem.item_type.in_(legacy_types))
        if pipeline_stages:
            clauses.append(
                and_(
                    JobItem.item_type == ITEM_TYPE_ANALYSIS_PIPELINE_STAGE,
                    JobItem.stage_name.in_(pipeline_stages),
                )
            )
        if not clauses:
            return None
        return or_(*clauses) if len(clauses) > 1 else clauses[0]

    def release_stale_pipeline_stage_locks(self) -> int:
        """Release stale locks on pipeline stage items (per-worker lock timeouts)."""
        released = 0
        for worker_type in PIPELINE_STAGES_BY_WORKER:
            released += self.release_stale_locks(worker_type=worker_type)
        return released

    def reconcile_audio_analysis_pipeline_jobs(self) -> list[str]:
        """Unblock stuck pipeline jobs: stale locks, dependencies, parent status."""
        from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator

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

        if not job_ids:
            return []

        self.release_stale_pipeline_stage_locks()
        orch = AnalysisPipelineOrchestrator(items=self)
        finished: list[str] = []
        for job_id in job_ids:
            orch.refresh_dependencies(job_id)
            with Session(engine) as session:
                self.recompute_job_progress(session, job_id)
                session.commit()
                job = session.get(Job, job_id)
                if job is not None and job.status not in ("queued", "running"):
                    finished.append(job_id)
        return finished

    def recompute_job_progress(
        self,
        session: Session,
        job_id: str,
        *,
        include_track_progress: bool = True,
    ) -> None:
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
        if job.job_type == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE:
            pending += counts.get("blocked", 0)
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
            step = f"processing {terminal}/{total}"
            if (
                include_track_progress
                and job.job_type == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE
            ):
                tp_log = self.pipeline_track_progress(job_id)
                tt = tp_log.get("tracks_total") or 0
                if tt > 0:
                    done = tp_log.get("tracks_completed", 0) + tp_log.get("tracks_failed", 0)
                    step = f"processing tracks {done}/{tt} · items {terminal}/{total}"
            job.current_step = step
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
        total = sum(counts.values())
        terminal = sum(counts.get(s, 0) for s in TERMINAL_ITEM_STATUSES)
        if preserve_cancelled:
            job.current_step = "cancelled"
        elif total > 0:
            job.current_step = f"completed {terminal}/{total}"
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
            tp = self.pipeline_track_progress(job.id)
            result.update(tp)
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
        pipeline_job = False
        with Session(engine) as session:
            job = session.get(Job, job_id)
            pipeline_job = (
                job is not None and job.job_type == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE
            )
            count = self._items.cancel_non_terminal_for_job(session, job_id, now=now)
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
                self._events.append(
                    session,
                    job_id=job_id,
                    event_type="cancelled",
                    message="Job cancelled by user",
                    context={"cancelled_items": count},
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
                    + counts.get("blocked", 0)
                )
                if pending == 0 and sum(counts.values()) > 0:
                    self._apply_terminal_job_result(session, job, counts)
                    session.commit()
        if pipeline_job:
            self._maybe_refresh_pipeline_dependencies(job_id)
        return count

    def pipeline_stage_counts(self, job_id: str) -> dict[str, dict[str, int]]:
        engine = get_engine()
        with Session(engine) as session:
            return self._items.count_by_stage_name(session, job_id)

    def pipeline_track_progress(self, job_id: str) -> dict[str, int]:
        """Per-track progress: completed only when audio_cleanup succeeds."""
        from app.audio.pipeline.constants import STAGE_AUDIO_CLEANUP

        engine = get_engine()
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job is None:
                return {"tracks_total": 0, "tracks_completed": 0, "tracks_failed": 0, "tracks_pending": 0}
            try:
                existing = json.loads(job.result_json or "{}")
            except json.JSONDecodeError:
                existing = {}
            track_count = int(existing.get("track_count") or 0)
            cleanup_by_track: dict[int, str] = {}
            failed_tracks: set[int] = set()
            track_ids: set[int] = set()
            for item in self._items.list_for_job(session, job_id, limit=100_000, offset=0):
                if item.track_id is None:
                    continue
                tid = int(item.track_id)
                track_ids.add(tid)
                if item.stage_name == STAGE_AUDIO_CLEANUP:
                    cleanup_by_track[tid] = str(item.status)
                elif item.status == "failed":
                    failed_tracks.add(tid)
            if track_count <= 0:
                track_count = len(track_ids) or len(cleanup_by_track)
            completed = failed = pending = 0
            for tid in track_ids or set(cleanup_by_track.keys()):
                cleanup_status = cleanup_by_track.get(tid)
                if cleanup_status == "success":
                    completed += 1
                elif cleanup_status in ("failed", "cancelled"):
                    failed += 1
                elif tid in failed_tracks and cleanup_status in (
                    None,
                    "skipped",
                    "pending",
                    "blocked",
                ):
                    failed += 1
                else:
                    pending += 1
            if track_count > 0 and completed + failed + pending != track_count:
                pending = max(0, track_count - completed - failed)
            return {
                "tracks_total": track_count,
                "tracks_completed": completed,
                "tracks_failed": failed,
                "tracks_pending": pending,
            }

    def list_items(self, job_id: str, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        engine = get_engine()
        with Session(engine) as session:
            rows = self._items.list_for_job(session, job_id, limit=limit, offset=offset)
            return [_item_to_dict(r) for r in rows]

    def is_job_cancelled(self, job_id: str) -> bool:
        return self._jobs.is_cancelled(job_id)

    def _maybe_refresh_pipeline_dependencies(self, job_id: str) -> None:
        if settings.analysis_pipeline_tick_enabled:
            return
        engine = get_engine()
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job is None or job.job_type != JOB_TYPE_AUDIO_ANALYSIS_PIPELINE:
                return
        from app.audio.pipeline.audio_cleanup import PipelineAudioCleanupService
        from app.audio.pipeline.constants import (
            STAGE_AUDIO_CLEANUP,
            STAGE_FEATURE_AGGREGATION,
        )
        from app.audio.pipeline.feature_aggregation import PipelineFeatureAggregationService
        from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator

        try:
            downstream = (STAGE_FEATURE_AGGREGATION, STAGE_AUDIO_CLEANUP)
            AnalysisPipelineOrchestrator(items=self).refresh_dependencies(
                job_id,
                stage_names=downstream,
                limit=settings.analysis_pipeline_refresh_batch_size,
            )
            PipelineFeatureAggregationService(items=self).try_run_pending_for_job(job_id)
            PipelineAudioCleanupService(items=self).try_run_pending_for_job(job_id)
        except Exception:
            logger.exception(
                "Pipeline dependency refresh failed for job %s (worker continues)",
                job_id,
            )


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
