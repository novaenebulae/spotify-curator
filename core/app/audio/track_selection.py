from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_library import Track
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.features.track_selection import FeatureTrackSelectionService
from app.library.search import TrackSearchService
from app.observability.errors import ApiError
from app.settings.config import settings


class AudioTrackSelectionService:
    def __init__(
        self,
        *,
        features_repo: AudioFeaturesRepository | None = None,
        sources_repo: FeatureSourcesRepository | None = None,
        segments_repo: TrackSegmentsRepository | None = None,
        feature_selection: FeatureTrackSelectionService | None = None,
        search_service: TrackSearchService | None = None,
    ) -> None:
        self._features = features_repo or AudioFeaturesRepository()
        self._sources = sources_repo or FeatureSourcesRepository()
        self._segments = segments_repo or TrackSegmentsRepository()
        self._feature_selection = feature_selection or FeatureTrackSelectionService()
        self._search = search_service or TrackSearchService()

    def resolve_for_download(
        self,
        session: Session,
        *,
        track_ids: list[int] | None,
        filter_dict: dict[str, Any] | None,
        only_missing: bool,
        retry_failed: bool,
        limit: int | None,
    ) -> list[int]:
        max_limit = min(limit or settings.audio_enrich_default_limit, settings.audio_enrich_max_limit)
        if track_ids is not None:
            ids = self._feature_selection._validate_track_ids(session, track_ids)  # noqa: SLF001
        elif filter_dict:
            ids = self._feature_selection._ids_from_filter(session, filter_dict, max_limit)  # noqa: SLF001
        else:
            ids = list(session.execute(select(Track.id).order_by(Track.id).limit(max_limit)).scalars())

        if only_missing and not retry_failed:
            ids = [i for i in ids if not self._has_active_segments(session, i)]
        elif retry_failed:
            source = self._sources.get_by_name(session, "essentia_lowlevel")
            if source:
                failed = set(
                    self._features.list_track_ids_failed_source(
                        session, feature_source_id=source.id, limit=max_limit
                    )
                )
                ids = [i for i in ids if i in failed or not self._has_active_segments(session, i)]
        return ids[:max_limit]

    def resolve_for_analysis(
        self,
        session: Session,
        *,
        track_ids: list[int] | None,
        filter_dict: dict[str, Any] | None,
        only_missing: bool,
        retry_failed: bool,
        force_refresh: bool,
        limit: int | None,
        require_existing_segments: bool,
    ) -> list[int]:
        max_limit = min(limit or settings.audio_enrich_default_limit, settings.audio_enrich_max_limit)
        if track_ids is not None:
            ids = self._feature_selection._validate_track_ids(session, track_ids)  # noqa: SLF001
        elif filter_dict:
            ids = self._feature_selection._ids_from_filter(session, filter_dict, max_limit)  # noqa: SLF001
        else:
            ids = list(session.execute(select(Track.id).order_by(Track.id).limit(max_limit)).scalars())

        source = self._sources.get_by_name(session, "essentia_lowlevel")
        if source is None:
            raise ApiError(
                code="INTERNAL_ERROR",
                message="essentia_lowlevel source not seeded",
                status_code=500,
            )

        out: list[int] = []
        for tid in ids:
            if require_existing_segments and not self._has_active_segments(session, tid):
                continue
            if force_refresh:
                out.append(tid)
                continue
            if retry_failed:
                row = self._features.get_active_for_track_source(
                    session, track_id=tid, feature_source_id=source.id
                )
                if row and row.status == "failed":
                    out.append(tid)
                    continue
            if only_missing:
                row = self._features.get_active_for_track_source(
                    session, track_id=tid, feature_source_id=source.id
                )
                if row and row.status in ("success", "partial"):
                    continue
            else:
                out.append(tid)
                continue
            out.append(tid)
        return out[:max_limit]

    def _has_active_segments(self, session: Session, track_id: int) -> bool:
        segs = self._segments.list_active_with_file(session, track_id)
        return len(segs) > 0
