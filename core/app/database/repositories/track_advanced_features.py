from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models_advanced_features import TrackAdvancedFeature


@dataclass(frozen=True)
class AdvancedFeatureUpsertRow:
    track_id: int
    feature_name: str
    value_float: float | None
    confidence: float | None
    source: str
    model_name: str | None = None
    model_version: str | None = None
    model_hash: str | None = None
    pipeline_version: str | None = None
    aggregation_method: str | None = None
    status: str = "success"
    value_text: str | None = None
    value_json: str | None = None


def _advanced_row_key(row: AdvancedFeatureUpsertRow) -> tuple:
    return (
        row.track_id,
        row.feature_name,
        row.source,
        row.model_name,
        row.pipeline_version,
    )


class TrackAdvancedFeaturesRepository:
    def list_for_tracks(
        self,
        session: Session,
        track_ids: list[int],
        *,
        sources: tuple[str, ...] | None = None,
    ) -> list[TrackAdvancedFeature]:
        if not track_ids:
            return []
        stmt = select(TrackAdvancedFeature).where(TrackAdvancedFeature.track_id.in_(track_ids))
        if sources:
            stmt = stmt.where(TrackAdvancedFeature.source.in_(sources))
        return list(session.scalars(stmt).all())

    def get_active(
        self,
        session: Session,
        *,
        track_id: int,
        feature_name: str,
        source: str,
        model_name: str | None,
        pipeline_version: str | None,
    ) -> TrackAdvancedFeature | None:
        stmt = select(TrackAdvancedFeature).where(
            TrackAdvancedFeature.track_id == track_id,
            TrackAdvancedFeature.feature_name == feature_name,
            TrackAdvancedFeature.source == source,
            TrackAdvancedFeature.model_name == model_name,
            TrackAdvancedFeature.pipeline_version == pipeline_version,
        )
        return session.execute(stmt).scalar_one_or_none()

    def upsert_many(
        self,
        session: Session,
        rows: list[AdvancedFeatureUpsertRow],
    ) -> int:
        if not rows:
            return 0
        deduped: dict[tuple, AdvancedFeatureUpsertRow] = {}
        for row in rows:
            deduped[_advanced_row_key(row)] = row
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        written = 0
        for row in deduped.values():
            for attempt in range(3):
                try:
                    with session.begin_nested():
                        with session.no_autoflush:
                            existing = self.get_active(
                                session,
                                track_id=row.track_id,
                                feature_name=row.feature_name,
                                source=row.source,
                                model_name=row.model_name,
                                pipeline_version=row.pipeline_version,
                            )
                        if existing is not None:
                            session.execute(
                                delete(TrackAdvancedFeature).where(
                                    TrackAdvancedFeature.id == existing.id
                                )
                            )
                        session.add(
                            TrackAdvancedFeature(
                                track_id=row.track_id,
                                feature_name=row.feature_name,
                                value_float=row.value_float,
                                value_text=row.value_text,
                                value_json=row.value_json,
                                confidence=row.confidence,
                                source=row.source,
                                model_name=row.model_name,
                                model_version=row.model_version,
                                model_hash=row.model_hash,
                                pipeline_version=row.pipeline_version,
                                aggregation_method=row.aggregation_method,
                                status=row.status,
                                created_at=now,
                                updated_at=now,
                            )
                        )
                    written += 1
                    break
                except IntegrityError:
                    if attempt == 2:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        return written
