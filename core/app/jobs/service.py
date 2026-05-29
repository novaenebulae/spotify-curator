from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_jobs import Job


@dataclass(frozen=True)
class JobStatus:
    id: str
    job_type: str
    status: str
    progress_current: int
    progress_total: int
    current_step: str
    result_json: dict
    last_error: str
    created_at: str
    started_at: str | None
    finished_at: str | None


class JobService:
    def create(self, job_type: str) -> str:
        job_id = uuid.uuid4().hex
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        engine = get_engine()
        with Session(engine) as session:
            session.add(
                Job(
                    id=job_id,
                    job_type=job_type,
                    status="queued",
                    progress_current=0,
                    progress_total=0,
                    current_step="",
                    result_json="{}",
                    last_error="",
                    created_at=now,
                    started_at=None,
                    finished_at=None,
                )
            )
            session.commit()
        return job_id

    def get(self, job_id: str) -> JobStatus | None:
        engine = get_engine()
        with Session(engine) as session:
            row = session.get(Job, job_id)
            if row is None:
                return None
            return JobStatus(
                id=row.id,
                job_type=row.job_type,
                status=row.status,
                progress_current=row.progress_current,
                progress_total=row.progress_total,
                current_step=row.current_step,
                result_json=json.loads(row.result_json or "{}"),
                last_error=row.last_error,
                created_at=row.created_at.isoformat(),
                started_at=row.started_at.isoformat() if row.started_at else None,
                finished_at=row.finished_at.isoformat() if row.finished_at else None,
            )

    def start_background(self, job_id: str, fn: Callable[[], dict]) -> None:
        t = threading.Thread(target=self._run, args=(job_id, fn), daemon=True)
        t.start()

    def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        progress_current: int | None = None,
        progress_total: int | None = None,
        current_step: str | None = None,
        result_json: dict | None = None,
        last_error: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        engine = get_engine()
        with Session(engine) as session:
            row = session.get(Job, job_id)
            if row is None:
                return
            if status is not None:
                row.status = status
            if progress_current is not None:
                row.progress_current = progress_current
            if progress_total is not None:
                row.progress_total = progress_total
            if current_step is not None:
                row.current_step = current_step
            if result_json is not None:
                row.result_json = json.dumps(result_json)
            if last_error is not None:
                row.last_error = last_error
            if started_at is not None:
                row.started_at = started_at
            if finished_at is not None:
                row.finished_at = finished_at
            session.commit()

    def _run(self, job_id: str, fn: Callable[[], dict]) -> None:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        self.update(job_id, status="running", started_at=now)
        try:
            result = fn()
            finished = datetime.now(tz=UTC).replace(tzinfo=None)
            self.update(job_id, status="succeeded", result_json=result, finished_at=finished)
        except Exception as e:  # noqa: BLE001
            finished = datetime.now(tz=UTC).replace(tzinfo=None)
            self.update(job_id, status="failed", last_error=str(e), finished_at=finished)

