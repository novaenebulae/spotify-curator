from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_library import Track
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.database.repositories.tracks import TracksRepository
from app.library.schemas import TrackSearchFilters
from app.library.search import TrackSearchService
from app.observability.errors import ApiError
from app.settings.config import settings


class FeatureTrackSelectionService:
    def __init__(
        self,
        *,
        features_repo: AudioFeaturesRepository | None = None,
        sources_repo: FeatureSourcesRepository | None = None,
        tracks_repo: TracksRepository | None = None,
        search_service: TrackSearchService | None = None,
    ) -> None:
        self._features = features_repo or AudioFeaturesRepository()
        self._sources = sources_repo or FeatureSourcesRepository()
        self._tracks = tracks_repo or TracksRepository()
        self._search = search_service or TrackSearchService()

    def resolve_track_ids(
        self,
        session: Session,
        *,
        track_ids: list[int] | None,
        filter_dict: dict[str, Any] | None,
        only_missing: bool,
        retry_failed: bool,
        force_refresh: bool,
        limit: int | None,
    ) -> list[int]:
        max_limit = settings.reccobeats_enrich_max_limit
        effective_limit = min(limit or settings.reccobeats_enrich_default_limit, max_limit)

        source = self._sources.get_by_name(session, "reccobeats")
        if source is None:
            raise ApiError(
                code="INTERNAL_ERROR",
                message="reccobeats source not seeded",
                status_code=500,
            )

        if track_ids is not None:
            ids = self._validate_track_ids(session, track_ids)
        elif filter_dict:
            ids = self._ids_from_filter(session, filter_dict, effective_limit)
        elif retry_failed and not force_refresh:
            ids = self._features.list_track_ids_failed_source(
                session, feature_source_id=source.id, limit=effective_limit
            )
        elif force_refresh and not only_missing:
            ids = list(
                session.execute(select(Track.id).order_by(Track.id).limit(effective_limit)).scalars()
            )
        else:
            ids = self._features.list_track_ids_missing_source(
                session, feature_source_id=source.id, limit=effective_limit
            )

        if only_missing and not force_refresh and track_ids is None:
            covered = set(
                self._features.list_track_ids_with_status(
                    session,
                    feature_source_id=source.id,
                    statuses=("success", "partial"),
                )
            )
            ids = [i for i in ids if i not in covered]

        return ids[:effective_limit]

    def _validate_track_ids(self, session: Session, track_ids: list[int]) -> list[int]:
        unique = list(dict.fromkeys(track_ids))
        found = set(
            session.execute(select(Track.id).where(Track.id.in_(unique))).scalars().all()
        )
        missing = [i for i in unique if i not in found]
        if missing:
            raise ApiError(
                code="NOT_FOUND",
                message="Some track_ids were not found",
                status_code=404,
                details={"missing_track_ids": missing},
            )
        return unique

    def _ids_from_filter(
        self, session: Session, filter_dict: dict[str, Any], limit: int
    ) -> list[int]:
        filters = TrackSearchFilters.model_validate({**filter_dict, "page": 1, "page_size": limit})
        filter_payload = filters.model_dump(exclude_none=True)
        filter_payload["sort"] = filters.sort
        filter_payload["order"] = filters.order

        snapshot_track_ids = None
        if filters.snapshot_status:
            snapshot_track_ids = self._search._track_ids_for_snapshot_status(  # noqa: SLF001
                session, filters.snapshot_status
            )

        duplicate_track_ids = None
        if filters.duplicate_status:
            duplicate_track_ids = self._tracks.duplicate_isrc_track_ids(session)

        ids_query = self._tracks.build_ids_query(
            session,
            filters=filter_payload,
            snapshot_track_ids=snapshot_track_ids,
            duplicate_track_ids=duplicate_track_ids,
        )
        return list(session.execute(ids_query.limit(limit)).scalars())
