from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_features import AudioFeature, FeatureSource
from app.database.models_library import Track


class FeatureMergeService:
    """Minimal merge: highest-priority active source per track (phase 4 MVP)."""

    def recompute(
        self,
        session: Session,
        *,
        track_ids: list[int] | None = None,
        limit: int = 5000,
    ) -> dict[str, int]:
        sources = list(
            session.execute(
                select(FeatureSource)
                .where(FeatureSource.is_active.is_(True))
                .order_by(FeatureSource.priority.desc())
            ).scalars()
        )
        if track_ids is None:
            track_ids = list(session.execute(select(Track.id).order_by(Track.id).limit(limit)).scalars())
        updated = 0
        for tid in track_ids:
            rows = list(
                session.execute(
                    select(AudioFeature).where(
                        AudioFeature.track_id == tid,
                        AudioFeature.is_active.is_(True),
                        AudioFeature.status.in_(("success", "partial")),
                    )
                ).scalars()
            )
            if not rows:
                continue
            by_source = {r.feature_source_id: r for r in rows}
            winner = None
            for src in sources:
                if src.id in by_source:
                    winner = by_source[src.id]
                    break
            if winner is None:
                continue
            for r in rows:
                if r.id != winner.id and r.is_active:
                    r.is_active = False
                    updated += 1
        session.flush()
        return {"tracks_processed": len(track_ids), "deactivated_rows": updated}
