from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_job_items import WorkerHeartbeat


class WorkerHeartbeatsRepository:
    def get_by_worker_id(self, session: Session, worker_id: str) -> WorkerHeartbeat | None:
        return session.execute(
            select(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == worker_id)
        ).scalar_one_or_none()

    def upsert(
        self,
        session: Session,
        *,
        worker_id: str,
        worker_type: str,
        status: str,
        current_job_id: str | None,
        current_item_id: str | None,
        hostname: str | None,
        process_id: int | None,
        started_at: datetime,
        last_seen_at: datetime,
        metadata_json: str,
    ) -> WorkerHeartbeat:
        row = self.get_by_worker_id(session, worker_id)
        if row is None:
            row = WorkerHeartbeat(
                worker_id=worker_id,
                worker_type=worker_type,
                status=status,
                current_job_id=current_job_id,
                current_item_id=current_item_id,
                hostname=hostname,
                process_id=process_id,
                started_at=started_at,
                last_seen_at=last_seen_at,
                metadata_json=metadata_json,
            )
            session.add(row)
        else:
            row.worker_type = worker_type
            row.status = status
            row.current_job_id = current_job_id
            row.current_item_id = current_item_id
            row.hostname = hostname
            row.process_id = process_id
            row.last_seen_at = last_seen_at
            row.metadata_json = metadata_json
        session.flush()
        return row

    def list_recent(
        self,
        session: Session,
        *,
        since: datetime,
        worker_type: str | None = None,
    ) -> list[WorkerHeartbeat]:
        stmt = select(WorkerHeartbeat).where(WorkerHeartbeat.last_seen_at >= since)
        if worker_type:
            stmt = stmt.where(WorkerHeartbeat.worker_type == worker_type)
        stmt = stmt.order_by(WorkerHeartbeat.last_seen_at.desc())
        return list(session.scalars(stmt))
