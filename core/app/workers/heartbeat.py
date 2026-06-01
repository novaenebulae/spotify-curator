from __future__ import annotations

import json
import os
import socket
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.repositories.worker_heartbeats import WorkerHeartbeatsRepository
from app.settings.config import settings


class WorkerHeartbeatService:
    def __init__(self, *, repo: WorkerHeartbeatsRepository | None = None) -> None:
        self._repo = repo or WorkerHeartbeatsRepository()

    def register_or_update(
        self,
        *,
        worker_id: str,
        worker_type: str,
        status: str,
        current_job_id: str | None = None,
        current_item_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not settings.worker_heartbeats_enabled:
            return
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        engine = get_engine()
        with Session(engine) as session:
            existing = self._repo.get_by_worker_id(session, worker_id)
            started = existing.started_at if existing else now
            self._repo.upsert(
                session,
                worker_id=worker_id,
                worker_type=worker_type,
                status=status,
                current_job_id=current_job_id,
                current_item_id=current_item_id,
                hostname=socket.gethostname(),
                process_id=os.getpid(),
                started_at=started,
                last_seen_at=now,
                metadata_json=json.dumps(metadata or {}),
            )
            session.commit()

    def list_active(self, *, worker_type: str | None = None) -> list[dict[str, Any]]:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        since = now - timedelta(seconds=settings.job_worker_heartbeat_interval_seconds * 3)
        engine = get_engine()
        with Session(engine) as session:
            rows = self._repo.list_recent(session, since=since, worker_type=worker_type)
            return [
                {
                    "worker_id": r.worker_id,
                    "worker_type": r.worker_type,
                    "status": r.status,
                    "current_job_id": r.current_job_id,
                    "current_item_id": r.current_item_id,
                    "hostname": r.hostname,
                    "process_id": r.process_id,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
                    "metadata": json.loads(r.metadata_json or "{}"),
                }
                for r in rows
            ]