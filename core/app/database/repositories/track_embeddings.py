from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_track_embeddings import TrackEmbedding


@dataclass(frozen=True)
class TrackEmbeddingUpsertRow:
    track_id: int
    source: str
    model_name: str
    dimension: int
    vector_json: str
    model_version: str | None = None
    model_hash: str | None = None
    aggregation_method: str | None = None
    segments_used: int | None = None
    pipeline_version: str | None = None
    status: str = "success"
    confidence: float | None = None


class TrackEmbeddingsRepository:
    def list_for_tracks(
        self, session: Session, track_ids: list[int]
    ) -> list[TrackEmbedding]:
        if not track_ids:
            return []
        return list(
            session.scalars(
                select(TrackEmbedding).where(TrackEmbedding.track_id.in_(track_ids))
            )
        )

    def get_for_track(
        self,
        session: Session,
        *,
        track_id: int,
        source: str,
        model_name: str,
        pipeline_version: str | None,
    ) -> TrackEmbedding | None:
        stmt = select(TrackEmbedding).where(
            TrackEmbedding.track_id == track_id,
            TrackEmbedding.source == source,
            TrackEmbedding.model_name == model_name,
            TrackEmbedding.pipeline_version == pipeline_version,
        )
        return session.execute(stmt).scalar_one_or_none()

    def upsert(self, session: Session, row: TrackEmbeddingUpsertRow) -> TrackEmbedding:
        existing = self.get_for_track(
            session,
            track_id=row.track_id,
            source=row.source,
            model_name=row.model_name,
            pipeline_version=row.pipeline_version,
        )
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        if existing is not None:
            existing.model_version = row.model_version
            existing.model_hash = row.model_hash
            existing.dimension = row.dimension
            existing.vector_json = row.vector_json
            existing.aggregation_method = row.aggregation_method
            existing.segments_used = row.segments_used
            existing.status = row.status
            existing.confidence = row.confidence
            existing.updated_at = now
            session.flush()
            return existing

        entity = TrackEmbedding(
            track_id=row.track_id,
            source=row.source,
            model_name=row.model_name,
            model_version=row.model_version,
            model_hash=row.model_hash,
            dimension=row.dimension,
            vector_json=row.vector_json,
            aggregation_method=row.aggregation_method,
            segments_used=row.segments_used,
            pipeline_version=row.pipeline_version,
            status=row.status,
            confidence=row.confidence,
            created_at=now,
            updated_at=now,
        )
        session.add(entity)
        session.flush()
        return entity

    @staticmethod
    def parse_vector(embedding: TrackEmbedding) -> list[float]:
        raw = json.loads(embedding.vector_json or "[]")
        if not isinstance(raw, list):
            raise ValueError("vector_json must be a JSON list")
        return [float(x) for x in raw]
