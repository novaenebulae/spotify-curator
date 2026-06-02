from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models_library import Track
from app.database.models_previews import TrackPreview


class TrackPreviewsRepository:
    def get_for_track_provider(
        self, session: Session, *, track_id: int, provider: str
    ) -> TrackPreview | None:
        return session.execute(
            select(TrackPreview).where(
                TrackPreview.track_id == track_id,
                TrackPreview.provider == provider,
            )
        ).scalar_one_or_none()

    def get_best_for_track(self, session: Session, track_id: int) -> TrackPreview | None:
        return session.execute(
            select(TrackPreview)
            .where(
                TrackPreview.track_id == track_id,
                TrackPreview.is_available.is_(True),
                TrackPreview.preview_url.is_not(None),
            )
            .order_by(TrackPreview.match_confidence.desc().nullslast())
            .limit(1)
        ).scalar_one_or_none()

    def upsert(
        self,
        session: Session,
        *,
        track_id: int,
        provider: str,
        fields: dict,
    ) -> TrackPreview:
        row = self.get_for_track_provider(session, track_id=track_id, provider=provider)
        now = datetime.utcnow()
        if row is None:
            row = TrackPreview(track_id=track_id, provider=provider, created_at=now)
            session.add(row)
        for key, val in fields.items():
            setattr(row, key, val)
        row.updated_at = now
        session.flush()
        return row

    def list_track_ids_missing(
        self,
        session: Session,
        *,
        provider: str,
        limit: int | None = None,
    ) -> list[int]:
        subq = (
            select(TrackPreview.track_id)
            .where(
                TrackPreview.provider == provider,
                TrackPreview.is_available.is_(True),
                TrackPreview.preview_url.is_not(None),
            )
        )
        stmt = (
            select(Track.id)
            .where(Track.id.not_in(subq))
            .order_by(Track.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(session.scalars(stmt))

    def coverage_summary(self, session: Session) -> dict[str, int | float]:
        total = int(session.scalar(select(func.count()).select_from(Track)) or 0)
        with_deezer = int(
            session.scalar(
                select(func.count())
                .select_from(TrackPreview)
                .where(
                    TrackPreview.provider == "deezer",
                    TrackPreview.is_available.is_(True),
                    TrackPreview.preview_url.is_not(None),
                )
            )
            or 0
        )
        with_any = int(
            session.scalar(
                select(func.count(func.distinct(TrackPreview.track_id))).where(
                    TrackPreview.is_available.is_(True),
                    TrackPreview.preview_url.is_not(None),
                )
            )
            or 0
        )
        failed = int(
            session.scalar(
                select(func.count())
                .select_from(TrackPreview)
                .where(
                    TrackPreview.provider == "deezer",
                    TrackPreview.is_available.is_(False),
                    TrackPreview.last_error.is_not(None),
                )
            )
            or 0
        )
        missing = max(0, total - with_any)
        pct = (with_any / total * 100.0) if total else 0.0
        return {
            "track_count": total,
            "with_any_preview": with_any,
            "with_deezer_preview": with_deezer,
            "missing_preview": missing,
            "failed_preview": failed,
            "coverage_percent": round(pct, 2),
        }
