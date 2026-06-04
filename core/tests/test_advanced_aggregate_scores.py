from __future__ import annotations

import pytest

from app.features.advanced.aggregate import aggregate_track_classifier_features


def test_aggregate_preserves_distinct_classifier_medians() -> None:
    segments = [
        {
            "mood_happy": {
                "model_key": "mood_happy",
                "model_status": "available",
                "probability": 0.02,
                "inference_mode": "real",
            },
            "approachability": {
                "model_key": "approachability",
                "model_status": "available",
                "probability": 0.55,
                "inference_mode": "real",
            },
        },
        {
            "mood_happy": {
                "model_key": "mood_happy",
                "model_status": "available",
                "probability": 0.04,
                "inference_mode": "real",
            },
            "approachability": {
                "model_key": "approachability",
                "model_status": "available",
                "probability": 0.61,
                "inference_mode": "real",
            },
        },
    ]
    aggregated = {a.feature_name: a.value for a in aggregate_track_classifier_features(segments)}
    assert aggregated["mood_happy_score"] != aggregated["approachability"]
    assert aggregated["mood_happy_score"] == pytest.approx(0.03, abs=0.01)
    assert aggregated["approachability"] == pytest.approx(0.58, abs=0.01)
