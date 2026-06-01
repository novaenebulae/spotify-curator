from __future__ import annotations

from app.features.reccobeats_mapper import map_reccobeats_features, map_reccobeats_result
from app.reccobeats.schemas import (
    ReccoBeatsArtist,
    ReccoBeatsAudioFeatures,
    ReccoBeatsFetchResult,
    ReccoBeatsTrackMeta,
)
from tests.fixtures.reccobeats_responses import RECCOBEATS_TRACK_ID, SAMPLE_FEATURES, SAMPLE_TRACK


def _full_features() -> ReccoBeatsAudioFeatures:
    return ReccoBeatsAudioFeatures(
        acousticness=SAMPLE_FEATURES["acousticness"],
        danceability=SAMPLE_FEATURES["danceability"],
        energy=SAMPLE_FEATURES["energy"],
        instrumentalness=SAMPLE_FEATURES["instrumentalness"],
        key=SAMPLE_FEATURES["key"],
        liveness=SAMPLE_FEATURES["liveness"],
        loudness=SAMPLE_FEATURES["loudness"],
        mode=SAMPLE_FEATURES["mode"],
        speechiness=SAMPLE_FEATURES["speechiness"],
        tempo=SAMPLE_FEATURES["tempo"],
        valence=SAMPLE_FEATURES["valence"],
        time_signature=SAMPLE_FEATURES["timeSignature"],
        duration_ms=SAMPLE_FEATURES["durationMs"],
    )


def test_map_full_payload_success() -> None:
    track = ReccoBeatsTrackMeta(
        id=RECCOBEATS_TRACK_ID,
        track_title=SAMPLE_TRACK["trackTitle"],
        artists=[ReccoBeatsArtist(id="a1", name="Taylor Swift")],
        duration_ms=SAMPLE_TRACK["durationMs"],
        isrc=SAMPLE_TRACK["isrc"],
        href=SAMPLE_TRACK["href"],
    )
    result = ReccoBeatsFetchResult(
        track=track,
        features=_full_features(),
        track_raw=SAMPLE_TRACK,
        features_raw=SAMPLE_FEATURES,
    )
    row = map_reccobeats_result(result, local_isrc=SAMPLE_TRACK["isrc"])

    assert row.status == "success"
    assert row.bpm == 93.5
    assert row.energy == 0.72
    assert row.bpm_confidence == 1.0
    assert row.feature_confidence == 1.0
    assert row.external_track_id == RECCOBEATS_TRACK_ID


def test_map_partial_payload() -> None:
    features = ReccoBeatsAudioFeatures(tempo=120.0, energy=0.5)
    track = ReccoBeatsTrackMeta(
        id=RECCOBEATS_TRACK_ID,
        track_title="Partial",
        artists=[],
        duration_ms=None,
        isrc=None,
        href=None,
    )
    row = map_reccobeats_features(features, track_meta=track, match_confidence=0.9)

    assert row.status == "partial"
    assert row.bpm == 120.0
    assert row.danceability is None
    assert row.feature_confidence > 0


def test_map_not_found() -> None:
    result = ReccoBeatsFetchResult(track=None, features=None)
    row = map_reccobeats_result(result)
    assert row.status == "not_found"
    assert row.error_code == "RECCOBEATS_NOT_FOUND"
