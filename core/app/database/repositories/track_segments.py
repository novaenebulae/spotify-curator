from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database.models_audio import TrackSegment


class TrackSegmentsRepository:
    def get(self, session: Session, segment_id: int) -> TrackSegment | None:
        return session.get(TrackSegment, segment_id)

    def list_for_track(
        self,
        session: Session,
        track_id: int,
        *,
        include_deleted: bool = False,
    ) -> list[TrackSegment]:
        stmt = select(TrackSegment).where(TrackSegment.track_id == track_id)
        if not include_deleted:
            stmt = stmt.where(TrackSegment.deleted_at.is_(None))
        stmt = stmt.order_by(TrackSegment.segment_type.asc())
        return list(session.scalars(stmt))

    def list_active_with_file(self, session: Session, track_id: int) -> list[TrackSegment]:
        stmt = (
            select(TrackSegment)
            .where(
                TrackSegment.track_id == track_id,
                TrackSegment.deleted_at.is_(None),
                TrackSegment.temporary_path.is_not(None),
            )
            .order_by(TrackSegment.segment_type.asc())
        )
        return list(session.scalars(stmt))

    def insert(self, session: Session, segment: TrackSegment) -> TrackSegment:
        session.add(segment)
        session.flush()
        return segment

    def update_fields(self, session: Session, segment_id: int, **fields: object) -> None:
        if fields:
            session.execute(
                update(TrackSegment).where(TrackSegment.id == segment_id).values(**fields)
            )

    def mark_deleted(self, session: Session, segment_id: int, *, deleted_at: datetime) -> None:
        self.update_fields(session, segment_id, deleted_at=deleted_at, temporary_path=None)

    def count_temp_files_for_track(self, session: Session, track_id: int) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(TrackSegment)
                .where(
                    TrackSegment.track_id == track_id,
                    TrackSegment.temporary_path.is_not(None),
                    TrackSegment.deleted_at.is_(None),
                )
            )
            or 0
        )
