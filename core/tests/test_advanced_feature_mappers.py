from __future__ import annotations

import pytest

from app.audio.essentia_aggregate import AggregatedFeatures
from app.features.advanced.aggregate import aggregate_track_classifier_features
from app.features.advanced.energy_proxy import compute_energy_proxy
from app.features.advanced.mappers import (
    binary_to_score,
    map_classifier_output,
    map_segment_outputs_to_features,
)
from app.features.advanced.raw_schemas import ClassifierSegmentOutput


def test_binary_to_score_from_probability() -> None:
    assert binary_to_score(0.7) == pytest.approx(0.7)
    assert binary_to_score({"probability": 0.2}) == pytest.approx(0.2)


def test_binary_to_score_from_logit() -> None:
    assert binary_to_score({"logit": 0.0}) == pytest.approx(0.5)


def test_map_mood_happy() -> None:
    out = ClassifierSegmentOutput(
        model_key="mood_happy",
        model_status="available",
        probability=0.8,
    )
    mapped = map_classifier_output("mood_happy", out)
    assert len(mapped) == 1
    assert mapped[0].feature_name == "mood_happy_score"
    assert mapped[0].value == pytest.approx(0.8)


def test_map_arousal_valence() -> None:
    out = ClassifierSegmentOutput(
        model_key="arousal_valence",
        model_status="available",
        arousal=-0.2,
        valence=0.6,
    )
    mapped = map_classifier_output("arousal_valence", out)
    names = {m.feature_name: m.value for m in mapped}
    assert "arousal" in names
    assert "valence_tf" in names
    assert names["arousal"] == pytest.approx(0.4)
    assert names["valence_tf"] == pytest.approx(0.6)


def test_map_arousal_valence_deam_scale() -> None:
    """DEAM MusicNN head emits ~1..9, not 0..1 (runtime logs H4)."""
    out = ClassifierSegmentOutput(
        model_key="arousal_valence",
        model_status="available",
        arousal=6.227352343107524,
        valence=5.780333493885241,
    )
    mapped = map_classifier_output("arousal_valence", out)
    names = {m.feature_name: m.value for m in mapped}
    assert names["arousal"] == pytest.approx((6.227352343107524 - 1.0) / 8.0, abs=1e-4)
    assert names["valence_tf"] == pytest.approx((5.780333493885241 - 1.0) / 8.0, abs=1e-4)
    assert names["arousal"] < 1.0
    assert names["valence_tf"] < 1.0


def test_map_voice_instrumental() -> None:
    out = ClassifierSegmentOutput(
        model_key="voice_instrumental",
        model_status="available",
        voice_probability=0.7,
        instrumental_probability=0.3,
    )
    mapped = map_classifier_output("voice_instrumental", out)
    names = {m.feature_name for m in mapped}
    assert names == {
        "voice_probability",
        "vocal_presence_score",
        "instrumental_focus_score",
    }


def test_map_electronic_acoustic_model_keys() -> None:
    elec = map_classifier_output(
        "mood_electronic",
        ClassifierSegmentOutput("mood_electronic", "available", probability=0.55),
    )
    assert elec[0].feature_name == "electronic_profile_score"
    ac = map_classifier_output(
        "mood_acoustic",
        ClassifierSegmentOutput("mood_acoustic", "available", probability=0.4),
    )
    assert ac[0].feature_name == "acoustic_profile_score"


def test_model_missing_returns_empty() -> None:
    out = ClassifierSegmentOutput("mood_happy", "missing", probability=0.5)
    assert map_classifier_output("mood_happy", out) == []


def test_aggregate_median_across_segments() -> None:
    segments = [
        {"mood_happy": {"model_key": "mood_happy", "model_status": "available", "probability": 0.2}},
        {"mood_happy": {"model_key": "mood_happy", "model_status": "available", "probability": 0.8}},
    ]
    agg = aggregate_track_classifier_features(segments)
    happy = next(a for a in agg if a.feature_name == "mood_happy_score")
    assert happy.value == pytest.approx(0.5)
    assert happy.status == "success"


def test_map_segment_outputs_to_features_integration() -> None:
    payload = {
        "danceability": {
            "model_key": "danceability",
            "model_status": "available",
            "probability": 0.65,
        },
        "approachability": {
            "model_key": "approachability",
            "model_status": "available",
            "probability": 0.42,
        },
    }
    mapped = map_segment_outputs_to_features(payload)
    names = {m.feature_name for m in mapped}
    assert "danceability_tf" in names
    assert "approachability" in names


def test_energy_proxy_from_aggregated_features() -> None:
    low = AggregatedFeatures(
        bpm=120.0,
        loudness=-10.0,
        dynamic_complexity=5.0,
        onset_rate=2.0,
    )
    value, conf = compute_energy_proxy(low)
    assert value is not None
    assert 0.0 <= value <= 1.0
    assert conf is not None
    assert conf > 0.5


def test_energy_proxy_disabled() -> None:
    low = AggregatedFeatures(bpm=120.0, loudness=-10.0)
    assert compute_energy_proxy(low, enabled=False) == (None, None)


def test_energy_proxy_insufficient_data() -> None:
    assert compute_energy_proxy({}) == (None, None)
