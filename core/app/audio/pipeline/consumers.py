from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    ACTIVE_SEGMENT_CONSUMER_STATUSES,
    SEGMENT_CONSUMER_STAGES,
)
from app.database.models_job_items import JobItem


def consumer_group_for_segment(segment_id: int) -> str:
    return f"segment:{segment_id}"


def segment_has_active_consumers(session: Session, *, segment_id: int) -> bool:
    """Return True while pipeline analysis stages still need the segment file."""
    group = consumer_group_for_segment(segment_id)
    row = session.execute(
        select(JobItem.id)
        .where(
            JobItem.consumer_group == group,
            JobItem.stage_name.in_(tuple(SEGMENT_CONSUMER_STAGES)),
            JobItem.status.in_(tuple(ACTIVE_SEGMENT_CONSUMER_STATUSES)),
        )
        .limit(1)
    ).first()
    return row is not None


def segment_cleanup_allowed(session: Session, *, segment_id: int) -> bool:
    return not segment_has_active_consumers(session, segment_id=segment_id)
