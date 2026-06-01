from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_features import FeatureSource


class FeatureSourcesRepository:
    def get_by_name(self, session: Session, name: str) -> FeatureSource | None:
        return session.execute(
            select(FeatureSource).where(FeatureSource.name == name)
        ).scalar_one_or_none()

    def get_by_id(self, session: Session, source_id: int) -> FeatureSource | None:
        return session.get(FeatureSource, source_id)

    def list_active(self, session: Session) -> list[FeatureSource]:
        return list(
            session.execute(
                select(FeatureSource).where(FeatureSource.is_active.is_(True)).order_by(FeatureSource.priority.desc())
            ).scalars()
        )

    def list_all(self, session: Session) -> list[FeatureSource]:
        stmt = select(FeatureSource).order_by(FeatureSource.priority.desc())
        return list(session.execute(stmt).scalars())
