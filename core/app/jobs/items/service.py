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
from app.jobs.items.constants import TERMINAL_ITEM_STATUSES, WORKER_ITEM_TYPES
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

    def reserve_next(
        self,
        *,
        worker_id: str,
        worker_type: str,
    ) -> ReservedJobItem | None:
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
                        SELECT id, job_id, item_type, track_id, segment_id, input_json, attempt_count
                        FROM job_items
                        WHERE status IN ('pending', 'rate_limited')
                          AND item_type IN ({placeholders})
                          AND (next_retry_at IS NULL OR next_retry_at <= :now)
                          AND (locked_by IS NULL OR locked_at < :stale_before)
                        ORDER BY priority DESC, created_at ASC
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
        job = session.get(Job, job_id)
        if job is None:
            return
        job.progress_total = total
        job.progress_current = terminal
        pending = counts.get("pending", 0) + counts.get("running", 0) + counts.get("rate_limited", 0)
        if pending == 0 and total > 0:
            failed = counts.get("failed", 0)
            success = counts.get("success", 0)
            if failed > 0 and success > 0:
                job.status = "partial"
            elif failed > 0 and success == 0:
                job.status = "failed"
            else:
                job.status = "succeeded"
            job.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
        session.flush()

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
            session.commit()
            if count:
                self.recompute_job_progress(session, job_id)
                session.commit()
            return count

    def list_items(self, job_id: str, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        engine = get_engine()
        with Session(engine) as session:
            rows = self._items.list_for_job(session, job_id, limit=limit, offset=offset)
            return [_item_to_dict(r) for r in rows]

    def is_job_cancelled(self, job_id: str) -> bool:
        return self._jobs.is_cancelled(job_id)


def _item_to_dict(row: JobItem) -> dict[str, Any]:
    return {
        "id": row.id,
        "job_id": row.job_id,
        "item_type": row.item_type,
        "track_id": row.track_id,
        "segment_id": row.segment_id,
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
