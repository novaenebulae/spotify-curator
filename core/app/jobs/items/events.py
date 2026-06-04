from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database.repositories.job_events import JobEventsRepository
from app.observability.redact import redact_dict
from app.settings.config import settings


class JobEventsService:
    def __init__(self, *, repo: JobEventsRepository | None = None) -> None:
        self._repo = repo or JobEventsRepository()

    def append(
        self,
        session: Session,
        *,
        job_id: str,
        event_type: str,
        message: str,
        item_id: str | None = None,
        level: str = "info",
        context: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> None:
        if not settings.job_events_enabled:
            return
        ctx = redact_dict(context or {})
        self._repo.append(
            session,
            job_id=job_id,
            item_id=item_id,
            level=level,
            event_type=event_type,
            message=redact_dict({"m": message})["m"] if message else "",
            context_json=json.dumps(ctx),
            created_at=datetime.now(tz=UTC).replace(tzinfo=None),
        )
        if commit:
            session.commit()

    def list_events(
        self,
        job_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        from app.database.engine import get_engine

        engine = get_engine()
        with Session(engine) as session:
            rows = self._repo.list_for_job(
                session,
                job_id,
                limit=limit,
                offset=offset,
                event_type=event_type,
            )
            return [_event_to_dict(r) for r in rows]


def _event_to_dict(row: object) -> dict[str, Any]:
    from app.database.models_job_items import JobEvent

    assert isinstance(row, JobEvent)
    try:
        context = json.loads(row.context_json or "{}")
    except json.JSONDecodeError:
        context = {}
    if not isinstance(context, dict):
        context = {}
    return {
        "id": row.id,
        "job_id": row.job_id,
        "item_id": row.item_id,
        "level": row.level,
        "event_type": row.event_type,
        "message": row.message,
        "context": redact_dict(context),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
