from __future__ import annotations

import logging
import os
import signal
import threading
import time
import uuid
from abc import ABC, abstractmethod

from sqlalchemy.exc import OperationalError

from app.jobs.items.service import JobItemService
from app.settings.config import settings
from app.workers.heartbeat import WorkerHeartbeatService

logger = logging.getLogger(__name__)


def _is_sqlite_locked(exc: OperationalError) -> bool:
    orig = getattr(exc, "orig", None)
    return orig is not None and "locked" in str(orig).lower()


class BaseWorker(ABC):
    worker_type: str

    def __init__(
        self,
        *,
        items: JobItemService | None = None,
        heartbeat: WorkerHeartbeatService | None = None,
    ) -> None:
        self._items = items or JobItemService()
        self._heartbeat = heartbeat or WorkerHeartbeatService()
        self._worker_id = f"{self.worker_type}-{os.getenv('HOSTNAME', 'local')}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self._running = True

    def run_forever(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_stop)
        signal.signal(signal.SIGINT, self._handle_stop)
        self._heartbeat.register_or_update(
            worker_id=self._worker_id,
            worker_type=self.worker_type,
            status="starting",
        )
        logger.info("Worker %s starting", self._worker_id)
        try:
            while self._running:
                try:
                    self._run_worker_iteration()
                except OperationalError as exc:
                    if not _is_sqlite_locked(exc):
                        raise
                    logger.warning(
                        "SQLite locked in worker loop, backing off: %s",
                        self._worker_id,
                    )
                    time.sleep(settings.job_worker_heartbeat_interval_seconds)
        finally:
            self._heartbeat.register_or_update(
                worker_id=self._worker_id,
                worker_type=self.worker_type,
                status="stopping",
            )
            logger.info("Worker %s stopped", self._worker_id)

    def _run_worker_iteration(self) -> None:
        self._heartbeat.register_or_update(
            worker_id=self._worker_id,
            worker_type=self.worker_type,
            status="idle",
        )
        self._items.release_stale_locks(worker_type=self.worker_type)
        item = self._items.reserve_next(
            worker_id=self._worker_id,
            worker_type=self.worker_type,
        )
        if item is None:
            self._heartbeat.register_or_update(
                worker_id=self._worker_id,
                worker_type=self.worker_type,
                status="idle",
            )
            time.sleep(settings.job_worker_heartbeat_interval_seconds)
            return
        if self._items.is_job_cancelled(item.job_id):
            self._items.mark_skipped(item.id, reason="Parent job cancelled")
            return
        self._process_item_with_heartbeat(item)

    def _handle_stop(self, *_args: object) -> None:
        self._running = False

    def _process_item_with_heartbeat(self, item: object) -> None:
        from app.jobs.items.service import ReservedJobItem

        assert isinstance(item, ReservedJobItem)
        stop = threading.Event()

        def _pulse() -> None:
            while not stop.wait(timeout=settings.job_worker_heartbeat_interval_seconds):
                self._heartbeat_running(
                    current_job_id=item.job_id,
                    current_item_id=item.id,
                    metadata=heartbeat_meta,
                )

        heartbeat_meta: dict[str, object] | None = None
        if item.stage_name:
            heartbeat_meta = {"stage_name": item.stage_name}
        self._heartbeat_running(
            current_job_id=item.job_id,
            current_item_id=item.id,
            metadata=heartbeat_meta,
        )
        pulse_thread = threading.Thread(target=_pulse, daemon=True)
        pulse_thread.start()
        try:
            self.process_item(item)
        except Exception as e:  # noqa: BLE001
            logger.exception("Item %s failed: %s", item.id, e)
            self._items.mark_failed(
                item.id,
                error_code="WORKER_ERROR",
                error_message=str(e)[:500],
                retryable=True,
            )
        finally:
            stop.set()
            pulse_thread.join(timeout=1.0)

    def _heartbeat_running(
        self,
        *,
        current_job_id: str | None = None,
        current_item_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Refresh heartbeat while a long-running item is processed."""
        self._heartbeat.register_or_update(
            worker_id=self._worker_id,
            worker_type=self.worker_type,
            status="running",
            current_job_id=current_job_id,
            current_item_id=current_item_id,
            metadata=metadata,
        )

    @abstractmethod
    def process_item(self, item: object) -> None: ...
