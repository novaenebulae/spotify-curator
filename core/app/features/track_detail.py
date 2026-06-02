from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_features import AudioFeature, AudioFeatureRawPayload, FeatureSource
from app.database.models_library import Track
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.features.confidence import FEATURE_FIELD_NAMES
from app.features.schemas import (
    TrackFeatureAvailabilityOut,
    TrackFeatureMergedOut,
    TrackFeatureMetaOut,
    TrackFeaturesResponse,
    TrackFeatureSourceOut,
)
from app.observability.errors import ApiError
from app.settings.config import settings


def _row_fields(row: AudioFeature) -> dict[str, float | int]:
    out: dict[str, float | int] = {}
    for name in FEATURE_FIELD_NAMES:
        val = getattr(row, name, None)
        if val is not None:
            out[name] = val
    return out


def _parse_essentia_extended(payload_json: str) -> dict[str, Any]:
    try:
        data = json.loads(payload_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    aggregated = data.get("aggregated")
    if not isinstance(aggregated, dict):
        aggregated = {}
    extended: dict[str, Any] = {}
    for key in (
        "mfcc",
        "hpcp",
        "spectral_centroid",
        "spectral_rolloff",
        "spectral_contrast",
        "dynamic_complexity",
        "onset_rate",
        "analysis_decision",
        "segment_count",
    ):
        if key in aggregated and aggregated[key] is not None:
            extended[key] = aggregated[key]
    segments_used = data.get("segments_used")
    if segments_used is not None:
        extended["segments_used"] = segments_used
    return extended


def _merged_from_row(row: AudioFeature, source: FeatureSource, *, extended: dict[str, Any]) -> TrackFeatureMergedOut:
    meta = TrackFeatureMetaOut(
        pipeline_version=settings.essentia_lowlevel_pipeline_version
        if source.name == "essentia_lowlevel"
        else None,
        segments_used=int(extended["segments_used"]) if extended.get("segments_used") is not None else None,
        analysis_decision=str(extended["analysis_decision"])
        if extended.get("analysis_decision")
        else None,
        external_track_id=row.external_track_id,
    )
    return TrackFeatureMergedOut(
        primary_source=source.name,
        display_name=source.display_name or source.name,
        is_active=row.is_active,
        status=row.status,
        feature_confidence=row.feature_confidence,
        error_code=row.error_code,
        error_message=row.error_message,
        fields=_row_fields(row),
        meta=meta,
        fetched_at=row.fetched_at.isoformat() if row.fetched_at else None,
    )


def _source_from_row(
    row: AudioFeature,
    source: FeatureSource,
    *,
    extended: dict[str, Any] | None = None,
) -> TrackFeatureSourceOut:
    pipeline_version = None
    if source.name == "essentia_lowlevel":
        pipeline_version = settings.essentia_lowlevel_pipeline_version
    return TrackFeatureSourceOut(
        source_name=source.name,
        display_name=source.display_name or source.name,
        is_active=row.is_active,
        status=row.status,
        feature_confidence=row.feature_confidence,
        error_code=row.error_code,
        error_message=row.error_message,
        fields=_row_fields(row),
        extended=extended or {},
        pipeline_version=pipeline_version,
        fetched_at=row.fetched_at.isoformat() if row.fetched_at else None,
    )


class TrackFeaturesService:
    def __init__(self, *, features_repo: AudioFeaturesRepository | None = None) -> None:
        self._features = features_repo or AudioFeaturesRepository()

    def get_track_features(self, session: Session, track_id: int) -> TrackFeaturesResponse:
        track = session.get(Track, track_id)
        if track is None:
            raise ApiError(code="NOT_FOUND", message="Track not found.", status_code=404)

        rows = list(
            session.execute(
                select(AudioFeature, FeatureSource)
                .join(FeatureSource, FeatureSource.id == AudioFeature.feature_source_id)
                .where(AudioFeature.track_id == track_id)
                .order_by(AudioFeature.fetched_at.desc().nullslast(), AudioFeature.id.desc())
            ).all()
        )

        by_source: dict[str, tuple[AudioFeature, FeatureSource]] = {}
        for af, src in rows:
            if src.name not in by_source:
                by_source[src.name] = (af, src)

        sources_out: list[TrackFeatureSourceOut] = []
        has_reccobeats = False
        has_essentia = False

        for name, (af, src) in sorted(by_source.items(), key=lambda x: x[0]):
            extended: dict[str, Any] | None = None
            if name == "essentia_lowlevel":
                has_essentia = af.status in ("success", "partial", "failed")
                raw = session.execute(
                    select(AudioFeatureRawPayload)
                    .where(
                        AudioFeatureRawPayload.track_id == track_id,
                        AudioFeatureRawPayload.feature_source_id == src.id,
                    )
                    .order_by(AudioFeatureRawPayload.fetched_at.desc().nullslast())
                    .limit(1)
                ).scalar_one_or_none()
                if raw and raw.payload_json:
                    extended = _parse_essentia_extended(raw.payload_json)
            elif name == "reccobeats":
                has_reccobeats = af.status in ("success", "partial", "failed", "not_found")
            sources_out.append(_source_from_row(af, src, extended=extended))

        merged: TrackFeatureMergedOut | None = None
        active_row = next((af for af, _ in rows if af.is_active), None)
        if active_row is not None:
            src = session.get(FeatureSource, active_row.feature_source_id)
            if src is not None:
                extended: dict[str, Any] = {}
                if src.name == "essentia_lowlevel":
                    raw = session.execute(
                        select(AudioFeatureRawPayload)
                        .where(
                            AudioFeatureRawPayload.track_id == track_id,
                            AudioFeatureRawPayload.feature_source_id == src.id,
                        )
                        .order_by(AudioFeatureRawPayload.fetched_at.desc().nullslast())
                        .limit(1)
                    ).scalar_one_or_none()
                    if raw and raw.payload_json:
                        extended = _parse_essentia_extended(raw.payload_json)
                merged = _merged_from_row(active_row, src, extended=extended)

        has_any = any(s.status in ("success", "partial") for s in sources_out)

        return TrackFeaturesResponse(
            track_id=track_id,
            merged=merged,
            sources=sources_out,
            availability=TrackFeatureAvailabilityOut(
                has_any_features=has_any,
                has_reccobeats=has_reccobeats
                and any(s.source_name == "reccobeats" and s.status in ("success", "partial") for s in sources_out),
                has_essentia_lowlevel=has_essentia
                and any(
                    s.source_name == "essentia_lowlevel" and s.status in ("success", "partial") for s in sources_out
                ),
                other_sources_count=len(
                    [s for s in sources_out if s.source_name not in ("reccobeats", "essentia_lowlevel")]
                ),
            ),
        )
