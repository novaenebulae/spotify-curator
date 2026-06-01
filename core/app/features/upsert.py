from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.essentia_aggregate import AggregatedFeatures
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.features.reccobeats_mapper import NormalizedFeatureRow, build_raw_payload_json
from app.reccobeats.schemas import ReccoBeatsFetchResult
from app.settings.config import settings


class FeatureUpsertService:
    def __init__(
        self,
        *,
        features_repo: AudioFeaturesRepository | None = None,
        sources_repo: FeatureSourcesRepository | None = None,
    ) -> None:
        self._features = features_repo or AudioFeaturesRepository()
        self._sources = sources_repo or FeatureSourcesRepository()

    def upsert_reccobeats(
        self,
        session: Session,
        *,
        track_id: int,
        fetch_result: ReccoBeatsFetchResult,
        normalized: NormalizedFeatureRow,
        force_refresh: bool = False,
        replace_failed: bool = False,
        payload_json: str | None = None,
    ) -> tuple[int, bool]:
        source = self._sources.get_by_name(session, "reccobeats")
        if source is None:
            raise RuntimeError("feature source reccobeats not seeded")

        now = datetime.now(tz=UTC).replace(tzinfo=None)
        request_key = normalized.external_track_id or fetch_result.track_raw.get("id")
        payload_json = payload_json or build_raw_payload_json(fetch_result)
        status_code = fetch_result.features_status_code or fetch_result.track_status_code

        self._features.insert_raw_payload(
            session,
            track_id=track_id,
            feature_source_id=source.id,
            request_key=str(request_key) if request_key else None,
            payload_json=payload_json,
            status_code=status_code,
            fetched_at=now,
        )

        existing = self._features.get_active_for_track_source(
            session, track_id=track_id, feature_source_id=source.id
        )

        if existing is not None and not force_refresh and not replace_failed:
            if existing.status in ("success", "partial"):
                return existing.id, False
            if existing.status in ("failed", "not_found") and normalized.status in (
                "failed",
                "not_found",
            ):
                return existing.id, False

        should_replace = force_refresh or replace_failed or existing is None
        if existing is not None and should_replace:
            self._features.deactivate_active_for_track_source(
                session, track_id=track_id, feature_source_id=source.id
            )

        if existing is not None and not should_replace:
            return existing.id, False

        is_active = normalized.status in ("success", "partial", "failed", "not_found")
        row = self._features.insert_feature(
            session,
            track_id=track_id,
            feature_source_id=source.id,
            columns=normalized.to_column_dict(),
            fetched_at=now,
            is_active=is_active,
        )

        if normalized.external_track_id:
            self._features.upsert_reccobeats_external_id(
                session,
                track_id=track_id,
                reccobeats_id=normalized.external_track_id,
            )

        return row.id, True

    def upsert_essentia_lowlevel(
        self,
        session: Session,
        *,
        track_id: int,
        aggregated: AggregatedFeatures,
        status: str = "success",
        error_code: str | None = None,
        error_message: str | None = None,
        force_refresh: bool = False,
        raw_payload_json: str | None = None,
    ) -> tuple[int, bool]:
        source = self._sources.get_by_name(session, "essentia_lowlevel")
        if source is None:
            raise RuntimeError("feature source essentia_lowlevel not seeded")

        now = datetime.now(tz=UTC).replace(tzinfo=None)
        payload = raw_payload_json or json.dumps(
            {
                "pipeline_version": settings.essentia_lowlevel_pipeline_version,
                "aggregated": aggregated.detail_json,
                "segments_used": aggregated.segments_used,
            }
        )
        self._features.insert_raw_payload(
            session,
            track_id=track_id,
            feature_source_id=source.id,
            request_key=settings.essentia_lowlevel_pipeline_version,
            payload_json=payload,
            status_code=200 if status == "success" else None,
            fetched_at=now,
        )

        existing = self._features.get_active_for_track_source(
            session, track_id=track_id, feature_source_id=source.id
        )
        if existing is not None and not force_refresh and existing.status in ("success", "partial"):
            return existing.id, False

        if existing is not None:
            self._features.deactivate_active_for_track_source(
                session, track_id=track_id, feature_source_id=source.id
            )

        columns = {
            "bpm": aggregated.bpm,
            "bpm_confidence": aggregated.bpm_confidence,
            "loudness": aggregated.loudness,
            "loudness_confidence": aggregated.feature_confidence,
            "key": aggregated.key,
            "key_confidence": aggregated.key_confidence,
            "mode": aggregated.mode,
            "mode_confidence": aggregated.key_confidence,
            "duration_ms": aggregated.duration_ms,
            "feature_confidence": aggregated.feature_confidence,
            "status": status,
            "error_code": error_code,
            "error_message": error_message,
        }
        row = self._features.insert_feature(
            session,
            track_id=track_id,
            feature_source_id=source.id,
            columns=columns,
            fetched_at=now,
            is_active=True,
        )
        return row.id, True
