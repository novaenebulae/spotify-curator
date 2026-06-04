from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database.models_job_items import JobItem
from app.database.models_jobs import Job


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

    def count_by_stage_name(self, session: Session, job_id: str) -> dict[str, dict[str, int]]:
        rows = session.execute(
            select(JobItem.stage_name, JobItem.status, func.count())
            .where(JobItem.job_id == job_id, JobItem.stage_name.is_not(None))
            .group_by(JobItem.stage_name, JobItem.status)
        ).all()
        result: dict[str, dict[str, int]] = {}
        for stage_name, status, count in rows:
            if stage_name is None:
                continue
            result.setdefault(str(stage_name), {})[str(status)] = int(count)
        return result

    def list_for_job_by_status(
        self,
        session: Session,
        job_id: str,
        *,
        status: str,
        limit: int = 10_000,
    ) -> list[JobItem]:
        stmt = (
            select(JobItem)
            .where(JobItem.job_id == job_id, JobItem.status == status)
            .order_by(JobItem.created_at.asc())
            .limit(limit)
        )
        return list(session.scalars(stmt))

    def get_dependents(self, session: Session, item_id: str) -> list[JobItem]:
        return list(
            session.scalars(
                select(JobItem).where(JobItem.depends_on_item_id == item_id)
            )
        )

    def find_pipeline_download_item(
        self,
        session: Session,
        *,
        job_id: str,
        track_id: int,
        item_id: str,
    ) -> JobItem | None:
        row = session.get(JobItem, item_id)
        if row is None:
            return None
        if row.job_id != job_id or row.track_id != track_id:
            return None
        if row.stage_name != "segment_download":
            return None
        return row

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
        return self.cancel_non_terminal_for_job(session, job_id, now=now)

    def cancel_non_terminal_for_job(self, session: Session, job_id: str, *, now: datetime) -> int:
        """Cancel queued pipeline/worker items. Running items finish cooperatively."""
        result = session.execute(
            update(JobItem)
            .where(
                JobItem.job_id == job_id,
                JobItem.status.in_(("pending", "rate_limited", "blocked")),
            )
            .values(status="cancelled", finished_at=now, locked_by=None, locked_at=None)
        )
        return int(result.rowcount or 0)

    def cancel_pending_for_terminal_parent_jobs(self, session: Session, *, now: datetime) -> int:
        """Drop queued items left behind when a worker job was cancelled without item cleanup."""
        terminal = ("cancelled", "failed", "succeeded", "partial")
        subq = select(Job.id).where(Job.status.in_(terminal))
        result = session.execute(
            update(JobItem)
            .where(
                JobItem.status.in_(("pending", "rate_limited")),
                JobItem.job_id.in_(subq),
            )
            .values(status="cancelled", finished_at=now, locked_by=None, locked_at=None)
        )
        return int(result.rowcount or 0)
