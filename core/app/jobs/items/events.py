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
