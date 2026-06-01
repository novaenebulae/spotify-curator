from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.features.confidence import (
    FEATURE_FIELD_NAMES,
    aggregate_confidence,
    compute_match_confidence,
    field_confidence,
)
from app.reccobeats.schemas import (
    ReccoBeatsAudioFeatures,
    ReccoBeatsFetchResult,
    ReccoBeatsTrackMeta,
)


@dataclass(frozen=True)
class NormalizedFeatureRow:
    bpm: float | None = None
    bpm_confidence: float | None = None
    energy: float | None = None
    energy_confidence: float | None = None
    danceability: float | None = None
    danceability_confidence: float | None = None
    valence: float | None = None
    valence_confidence: float | None = None
    acousticness: float | None = None
    acousticness_confidence: float | None = None
    instrumentalness: float | None = None
    instrumentalness_confidence: float | None = None
    speechiness: float | None = None
    speechiness_confidence: float | None = None
    liveness: float | None = None
    liveness_confidence: float | None = None
    loudness: float | None = None
    loudness_confidence: float | None = None
    key: int | None = None
    key_confidence: float | None = None
    mode: int | None = None
    mode_confidence: float | None = None
    time_signature: int | None = None
    duration_ms: int | None = None
    feature_confidence: float = 0.0
    status: str = "failed"
    external_track_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_column_dict(self) -> dict[str, Any]:
        return {
            "bpm": self.bpm,
            "bpm_confidence": self.bpm_confidence,
            "energy": self.energy,
            "energy_confidence": self.energy_confidence,
            "danceability": self.danceability,
            "danceability_confidence": self.danceability_confidence,
            "valence": self.valence,
            "valence_confidence": self.valence_confidence,
            "acousticness": self.acousticness,
            "acousticness_confidence": self.acousticness_confidence,
            "instrumentalness": self.instrumentalness,
            "instrumentalness_confidence": self.instrumentalness_confidence,
            "speechiness": self.speechiness,
            "speechiness_confidence": self.speechiness_confidence,
            "liveness": self.liveness,
            "liveness_confidence": self.liveness_confidence,
            "loudness": self.loudness,
            "loudness_confidence": self.loudness_confidence,
            "key": self.key,
            "key_confidence": self.key_confidence,
            "mode": self.mode,
            "mode_confidence": self.mode_confidence,
            "time_signature": self.time_signature,
            "duration_ms": self.duration_ms,
            "feature_confidence": self.feature_confidence,
            "status": self.status,
            "external_track_id": self.external_track_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


def map_reccobeats_result(
    result: ReccoBeatsFetchResult,
    *,
    local_isrc: str | None = None,
) -> NormalizedFeatureRow:
    if result.track is None:
        return NormalizedFeatureRow(
            status="not_found",
            error_code="RECCOBEATS_NOT_FOUND",
            error_message="Track not found on ReccoBeats",
        )

    if result.features is None:
        return NormalizedFeatureRow(
            status="not_found",
            external_track_id=result.track.id,
            error_code="RECCOBEATS_FEATURES_MISSING",
            error_message="Audio features not available on ReccoBeats",
        )

    isrc_match = bool(
        local_isrc and result.track.isrc and local_isrc.upper() == result.track.isrc.upper()
    )
    match_conf = compute_match_confidence(isrc_match=isrc_match, spotify_id_match=True)

    return map_reccobeats_features(
        result.features,
        track_meta=result.track,
        match_confidence=match_conf,
    )


def map_reccobeats_features(
    features: ReccoBeatsAudioFeatures,
    *,
    track_meta: ReccoBeatsTrackMeta | None = None,
    match_confidence: float = 1.0,
) -> NormalizedFeatureRow:
    source_values = {
        "bpm": features.tempo,
        "energy": features.energy,
        "danceability": features.danceability,
        "valence": features.valence,
        "acousticness": features.acousticness,
        "instrumentalness": features.instrumentalness,
        "speechiness": features.speechiness,
        "liveness": features.liveness,
        "loudness": features.loudness,
        "key": features.key,
        "mode": features.mode,
        "time_signature": features.time_signature,
        "duration_ms": features.duration_ms or (track_meta.duration_ms if track_meta else None),
    }

    field_map = {
        name: field_confidence(name, source_values[name], match_confidence=match_confidence)
        for name in FEATURE_FIELD_NAMES
    }
    feature_confidence, status = aggregate_confidence(field_map)

    row_kwargs: dict[str, Any] = {
        "feature_confidence": feature_confidence,
        "status": status,
        "external_track_id": track_meta.id if track_meta else None,
    }
    for name, fc in field_map.items():
        row_kwargs[name] = fc.value
        conf_key = f"{name}_confidence"
        if conf_key in NormalizedFeatureRow.__dataclass_fields__:
            row_kwargs[conf_key] = fc.confidence

    return NormalizedFeatureRow(**row_kwargs)


def build_raw_payload_json(result: ReccoBeatsFetchResult) -> str:
    payload = {
        "track": result.track_raw,
        "features": result.features_raw,
        "track_status_code": result.track_status_code,
        "features_status_code": result.features_status_code,
    }
    return json.dumps(payload)
