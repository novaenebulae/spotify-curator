from __future__ import annotations

from datetime import datetime

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
