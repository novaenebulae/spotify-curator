from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_job_items import JobEvent


class JobEventsRepository:
    def append(
        self,
        session: Session,
        *,
        job_id: str,
        item_id: str | None,
        level: str,
        event_type: str,
        message: str,
        context_json: str,
        created_at: datetime,
    ) -> JobEvent:
        row = JobEvent(
            job_id=job_id,
            item_id=item_id,
            level=level,
            event_type=event_type,
            message=message,
            context_json=context_json,
            created_at=created_at,
        )
        session.add(row)
        session.flush()
        return row

    def list_for_job(
        self,
        session: Session,
        job_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
        event_type: str | None = None,
    ) -> list[JobEvent]:
        stmt = select(JobEvent).where(JobEvent.job_id == job_id)
        if event_type:
            stmt = stmt.where(JobEvent.event_type == event_type)
        stmt = (
            stmt.order_by(JobEvent.created_at.desc(), JobEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt))
