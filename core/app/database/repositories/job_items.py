from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database.models_job_items import JobItem


class JobItemsRepository:
    def get(self, session: Session, item_id: str) -> JobItem | None:
        return session.get(JobItem, item_id)

    def list_for_job(
        self,
        session: Session,
        job_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JobItem]:
        stmt = (
            select(JobItem)
            .where(JobItem.job_id == job_id)
            .order_by(JobItem.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt))

    def count_for_job(self, session: Session, job_id: str) -> int:
        return int(
            session.scalar(select(func.count()).select_from(JobItem).where(JobItem.job_id == job_id))
            or 0
        )

    def count_by_status(self, session: Session, job_id: str) -> dict[str, int]:
        rows = session.execute(
            select(JobItem.status, func.count())
            .where(JobItem.job_id == job_id)
            .group_by(JobItem.status)
        ).all()
        return {str(status): int(count) for status, count in rows}

    def first_failed_for_job(self, session: Session, job_id: str) -> JobItem | None:
        return session.execute(
            select(JobItem)
            .where(JobItem.job_id == job_id, JobItem.status == "failed")
            .order_by(JobItem.finished_at.desc().nullslast(), JobItem.id.asc())
            .limit(1)
        ).scalar_one_or_none()

    def insert(self, session: Session, item: JobItem) -> JobItem:
        session.add(item)
        session.flush()
        return item

    def bulk_insert(self, session: Session, items: list[JobItem]) -> None:
        session.add_all(items)

    def update_fields(
        self,
        session: Session,
        item_id: str,
        **fields: object,
    ) -> None:
        if not fields:
            return
        session.execute(update(JobItem).where(JobItem.id == item_id).values(**fields))

    def cancel_pending_for_job(self, session: Session, job_id: str, *, now: datetime) -> int:
        result = session.execute(
            update(JobItem)
            .where(
                JobItem.job_id == job_id,
                JobItem.status.in_(("pending", "rate_limited")),
            )
            .values(status="cancelled", finished_at=now, locked_by=None, locked_at=None)
        )
        return int(result.rowcount or 0)
