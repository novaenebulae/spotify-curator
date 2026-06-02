from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database.models_features import AudioFeature, AudioFeatureRawPayload, FeatureSource
from app.database.models_library import ExternalId, Track


class AudioFeaturesRepository:
    def get_active_for_track_source(
        self, session: Session, *, track_id: int, feature_source_id: int
    ) -> AudioFeature | None:
        return session.execute(
            select(AudioFeature).where(
                AudioFeature.track_id == track_id,
                AudioFeature.feature_source_id == feature_source_id,
                AudioFeature.is_active.is_(True),
            )
        ).scalar_one_or_none()

    def deactivate_active_for_track_source(
        self, session: Session, *, track_id: int, feature_source_id: int
    ) -> None:
        session.execute(
            update(AudioFeature)
            .where(
                AudioFeature.track_id == track_id,
                AudioFeature.feature_source_id == feature_source_id,
                AudioFeature.is_active.is_(True),
            )
            .values(is_active=False, updated_at=datetime.now(tz=UTC).replace(tzinfo=None))
        )

    def insert_raw_payload(
        self,
        session: Session,
        *,
        track_id: int,
        feature_source_id: int,
        request_key: str | None,
        payload_json: str,
        status_code: int | None,
        fetched_at: datetime,
    ) -> AudioFeatureRawPayload:
        row = AudioFeatureRawPayload(
            track_id=track_id,
            feature_source_id=feature_source_id,
            request_key=request_key,
            payload_json=payload_json,
            status_code=status_code,
            fetched_at=fetched_at,
            created_at=fetched_at,
        )
        session.add(row)
        session.flush()
        return row

    def insert_feature(
        self,
        session: Session,
        *,
        track_id: int,
        feature_source_id: int,
        columns: dict,
        fetched_at: datetime,
        is_active: bool = True,
    ) -> AudioFeature:
        now = fetched_at
        row = AudioFeature(
            track_id=track_id,
            feature_source_id=feature_source_id,
            is_active=is_active,
            fetched_at=fetched_at,
            created_at=now,
            updated_at=now,
            **columns,
        )
        session.add(row)
        session.flush()
        return row

    def count_tracks_total(self, session: Session) -> int:
        return int(session.execute(select(func.count()).select_from(Track)).scalar_one())

    def count_with_active_source(
        self, session: Session, *, feature_source_id: int, statuses: tuple[str, ...]
    ) -> int:
        q = (
            select(func.count(func.distinct(AudioFeature.track_id)))
            .where(
                AudioFeature.feature_source_id == feature_source_id,
                AudioFeature.is_active.is_(True),
                AudioFeature.status.in_(statuses),
            )
        )
        return int(session.execute(q).scalar_one())

    def count_by_status(self, session: Session, *, feature_source_id: int, status: str) -> int:
        q = (
            select(func.count(func.distinct(AudioFeature.track_id)))
            .where(
                AudioFeature.feature_source_id == feature_source_id,
                AudioFeature.is_active.is_(True),
                AudioFeature.status == status,
            )
        )
        return int(session.execute(q).scalar_one())

    def count_field_available(
        self, session: Session, *, feature_source_id: int, field_name: str
    ) -> int:
        col = getattr(AudioFeature, field_name)
        q = select(func.count(func.distinct(AudioFeature.track_id))).where(
            AudioFeature.feature_source_id == feature_source_id,
            AudioFeature.is_active.is_(True),
            AudioFeature.status.in_(("success", "partial")),
            col.is_not(None),
        )
        return int(session.execute(q).scalar_one())

    def list_recent_failures(
        self,
        session: Session,
        *,
        feature_source_id: int,
        limit: int = 20,
    ) -> list[tuple[AudioFeature, Track]]:
        q = (
            select(AudioFeature, Track)
            .join(Track, Track.id == AudioFeature.track_id)
            .where(
                AudioFeature.feature_source_id == feature_source_id,
                AudioFeature.is_active.is_(True),
                AudioFeature.status.in_(("failed", "not_found")),
            )
            .order_by(AudioFeature.fetched_at.desc())
            .limit(limit)
        )
        return list(session.execute(q).all())

    def count_failures(
        self,
        session: Session,
        *,
        feature_source_ids: list[int],
        statuses: tuple[str, ...] = ("failed", "not_found"),
    ) -> int:
        q = (
            select(func.count())
            .select_from(AudioFeature)
            .where(
                AudioFeature.is_active.is_(True),
                AudioFeature.feature_source_id.in_(feature_source_ids),
                AudioFeature.status.in_(statuses),
            )
        )
        return int(session.execute(q).scalar_one())

    def list_failures_page(
        self,
        session: Session,
        *,
        feature_source_ids: list[int],
        offset: int,
        limit: int,
        statuses: tuple[str, ...] = ("failed", "not_found"),
    ) -> list[tuple[AudioFeature, Track, FeatureSource]]:
        q = (
            select(AudioFeature, Track, FeatureSource)
            .join(Track, Track.id == AudioFeature.track_id)
            .join(FeatureSource, FeatureSource.id == AudioFeature.feature_source_id)
            .where(
                AudioFeature.is_active.is_(True),
                AudioFeature.feature_source_id.in_(feature_source_ids),
                AudioFeature.status.in_(statuses),
            )
            .order_by(AudioFeature.fetched_at.desc().nullslast(), AudioFeature.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(q).all())

    def list_track_ids_missing_source(
        self, session: Session, *, feature_source_id: int, limit: int | None = None
    ) -> list[int]:
        subq = (
            select(AudioFeature.track_id)
            .where(
                AudioFeature.feature_source_id == feature_source_id,
                AudioFeature.is_active.is_(True),
                AudioFeature.status.in_(("success", "partial")),
            )
            .distinct()
        )
        q = select(Track.id).where(Track.id.not_in(subq)).order_by(Track.id)
        if limit is not None:
            q = q.limit(limit)
        return list(session.execute(q).scalars())

    def list_track_ids_failed_source(
        self, session: Session, *, feature_source_id: int, limit: int | None = None
    ) -> list[int]:
        q = (
            select(AudioFeature.track_id)
            .where(
                AudioFeature.feature_source_id == feature_source_id,
                AudioFeature.is_active.is_(True),
                AudioFeature.status == "failed",
            )
            .distinct()
            .order_by(AudioFeature.track_id)
        )
        if limit is not None:
            q = q.limit(limit)
        return list(session.execute(q).scalars())

    def upsert_reccobeats_external_id(
        self, session: Session, *, track_id: int, reccobeats_id: str
    ) -> None:
        existing = session.execute(
            select(ExternalId).where(
                ExternalId.track_id == track_id,
                ExternalId.id_type == "reccobeats_id",
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                ExternalId(
                    track_id=track_id,
                    id_type="reccobeats_id",
                    id_value=reccobeats_id,
                    source="reccobeats",
                    external_type="reccobeats_id",
                    confidence=1.0,
                )
            )
        else:
            existing.id_value = reccobeats_id
            existing.source = "reccobeats"
            existing.external_type = "reccobeats_id"
            existing.confidence = 1.0

    def list_track_ids_with_status(
        self,
        session: Session,
        *,
        feature_source_id: int,
        statuses: tuple[str, ...],
        limit: int | None = None,
    ) -> list[int]:
        q = (
            select(AudioFeature.track_id)
            .where(
                AudioFeature.feature_source_id == feature_source_id,
                AudioFeature.is_active.is_(True),
                AudioFeature.status.in_(statuses),
            )
            .distinct()
            .order_by(AudioFeature.track_id)
        )
        if limit is not None:
            q = q.limit(limit)
        return list(session.execute(q).scalars())

    def get_source_name_map(self, session: Session) -> dict[int, FeatureSource]:
        sources = session.execute(select(FeatureSource)).scalars().all()
        return {s.id: s for s in sources}
