from __future__ import annotations

import json
from typing import Any

from app.database.models_advanced_features import TrackAdvancedFeature

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_features import AudioFeature, AudioFeatureRawPayload, FeatureSource
from app.database.models_library import Track
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.database.repositories.track_advanced_features import TrackAdvancedFeaturesRepository
from app.database.repositories.track_embeddings import TrackEmbeddingsRepository
from app.features.confidence import FEATURE_FIELD_NAMES
from app.features.schemas import (
    AdvancedEmbeddingOut,
    AdvancedGenreOut,
    AdvancedScalarFeatureOut,
    EssentiaTensorFlowSourceOut,
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
        "segments_planned",
        "segments_analyzed",
        "segments_missing_reason",
    ):
        if key in aggregated and aggregated[key] is not None:
            extended[key] = aggregated[key]
    segments_used = data.get("segments_used")
    if segments_used is not None:
        extended["segments_used"] = segments_used
    for key in ("segments_planned", "segments_analyzed", "segments_missing_reason"):
        if key in data and data[key] is not None:
            extended[key] = data[key]
    return extended


def _merged_from_row(row: AudioFeature, source: FeatureSource, *, extended: dict[str, Any]) -> TrackFeatureMergedOut:
    meta = TrackFeatureMetaOut(
        pipeline_version=settings.essentia_lowlevel_pipeline_version
        if source.name == "essentia_lowlevel"
        else None,
        segments_used=int(extended["segments_used"]) if extended.get("segments_used") is not None else None,
        segments_planned=int(extended["segments_planned"])
        if extended.get("segments_planned") is not None
        else None,
        segments_analyzed=int(extended["segments_analyzed"])
        if extended.get("segments_analyzed") is not None
        else None,
        segments_missing_reason=str(extended["segments_missing_reason"])
        if extended.get("segments_missing_reason")
        else None,
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


_GENRE_FEATURE_NAMES = frozenset({"genre_discogs_519", "genre_discogs_519_top_k"})


class TrackFeaturesService:
    def __init__(
        self,
        *,
        features_repo: AudioFeaturesRepository | None = None,
        advanced_repo: TrackAdvancedFeaturesRepository | None = None,
        embeddings_repo: TrackEmbeddingsRepository | None = None,
    ) -> None:
        self._features = features_repo or AudioFeaturesRepository()
        self._advanced = advanced_repo or TrackAdvancedFeaturesRepository()
        self._embeddings = embeddings_repo or TrackEmbeddingsRepository()

    def get_track_features(
        self,
        session: Session,
        track_id: int,
        *,
        include_embedding_vector: bool = False,
    ) -> TrackFeaturesResponse:
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
        advanced_block = self._build_advanced_block(
            session,
            track_id,
            include_embedding_vector=include_embedding_vector,
        )
        has_tf = advanced_block is not None and advanced_block.status in ("success", "partial")

        return TrackFeaturesResponse(
            track_id=track_id,
            merged=merged,
            sources=sources_out,
            advanced=advanced_block,
            availability=TrackFeatureAvailabilityOut(
                has_any_features=has_any or has_tf,
                has_reccobeats=has_reccobeats
                and any(s.source_name == "reccobeats" and s.status in ("success", "partial") for s in sources_out),
                has_essentia_lowlevel=has_essentia
                and any(
                    s.source_name == "essentia_lowlevel" and s.status in ("success", "partial") for s in sources_out
                ),
                has_essentia_tensorflow=has_tf,
                other_sources_count=len(
                    [s for s in sources_out if s.source_name not in ("reccobeats", "essentia_lowlevel")]
                ),
            ),
        )

    def _build_advanced_block(
        self,
        session: Session,
        track_id: int,
        *,
        include_embedding_vector: bool,
    ) -> EssentiaTensorFlowSourceOut | None:
        rows = self._advanced.list_for_tracks(session, [track_id], sources=("essentia_tensorflow", "derived"))
        emb_rows = [
            e
            for e in self._embeddings.list_for_tracks(session, [track_id])
            if e.source == "essentia_tensorflow"
        ]
        if not rows and not emb_rows:
            return None

        by_name: dict[str, TrackAdvancedFeature] = {}
        for row in rows:
            prev = by_name.get(row.feature_name)
            if prev is None:
                by_name[row.feature_name] = row
                continue
            row_ts = row.updated_at or row.created_at
            prev_ts = prev.updated_at or prev.created_at
            if row_ts and prev_ts and row_ts > prev_ts:
                by_name[row.feature_name] = row
            elif row_ts and not prev_ts:
                by_name[row.feature_name] = row

        scalars: list[AdvancedScalarFeatureOut] = []
        overall_status = "missing"
        for name, row in sorted(by_name.items()):
            if name in _GENRE_FEATURE_NAMES:
                continue
            missing_reason = None
            if row.status == "model_missing":
                missing_reason = "MODEL_MISSING"
            elif row.value_float is None and row.status not in ("success", "partial"):
                missing_reason = "FEATURE_MISSING"
            scalars.append(
                AdvancedScalarFeatureOut(
                    feature_name=name,
                    value=row.value_float if row.value_float is not None else row.value_text,
                    confidence=row.confidence,
                    status=row.status,
                    model_name=row.model_name,
                    model_version=row.model_version,
                    pipeline_version=row.pipeline_version,
                    aggregation_method=row.aggregation_method,
                    missing_reason=missing_reason,
                )
            )
            if row.status in ("success", "partial"):
                overall_status = "success"
            elif row.status == "model_missing" and overall_status != "success":
                overall_status = "model_missing"

        genre_block: AdvancedGenreOut | None = None
        genre_row = by_name.get("genre_discogs_519")
        top_k_row = by_name.get("genre_discogs_519_top_k")
        if genre_row or top_k_row:
            label = genre_row.value_text if genre_row else None
            score = genre_row.value_float if genre_row else None
            top_k: list[dict] = []
            if top_k_row and top_k_row.value_json:
                try:
                    parsed = json.loads(top_k_row.value_json)
                    if isinstance(parsed, list):
                        top_k = [x for x in parsed[:10] if isinstance(x, dict)]
                except json.JSONDecodeError:
                    top_k = []
            genre_block = AdvancedGenreOut(label=label, score=score, top_k=top_k)

        embedding_block: AdvancedEmbeddingOut | None = None
        emb = max(emb_rows, key=lambda e: e.updated_at or e.created_at, default=None)
        if emb is not None:
            vector = None
            if include_embedding_vector:
                vector = self._embeddings.parse_vector(emb)
            embedding_block = AdvancedEmbeddingOut(
                status=emb.status,
                model_name=emb.model_name,
                dimension=emb.dimension,
                pipeline_version=emb.pipeline_version,
                aggregation_method=emb.aggregation_method,
                segments_used=emb.segments_used,
                confidence=emb.confidence,
                vector=vector,
            )
            if emb.status in ("success", "partial"):
                overall_status = "success"

        if not scalars and genre_block is None and embedding_block is None:
            return None

        return EssentiaTensorFlowSourceOut(
            status=overall_status,
            scalar_features=scalars,
            genre=genre_block,
            embedding=embedding_block,
        )
