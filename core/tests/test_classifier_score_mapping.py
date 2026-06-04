from __future__ import annotations

import pytest

from app.audio.tensorflow.classifier_runner import (
    _arousal_valence_scores,
    _binary_positive_probability,
    _regression_unit_score,
)


def test_binary_positive_uses_metadata_class_index() -> None:
    activations = [("aggressive", 0.131), ("not_aggressive", 0.869)]
    prob = _binary_positive_probability(
        activations, "aggressive", ["aggressive", "not_aggressive"]
    )
    assert prob == pytest.approx(0.131, abs=1e-6)


def test_arousal_valence_not_identical_fallback() -> None:
    activations = [("arousal", 0.2), ("valence", 0.8)]
    arousal, valence = _arousal_valence_scores(activations, ["arousal", "valence"])
    assert arousal == pytest.approx(0.2, abs=1e-6)
    assert valence == pytest.approx(0.8, abs=1e-6)
    assert arousal != valence


def test_regression_unit_sigmoid_for_negative_logit() -> None:
    score = _regression_unit_score([("approachability", -2.0)], "approachability_regression")
    assert score == pytest.approx(0.119, abs=0.01)
    assert score > 0.0


def test_binary_normalizes_logit() -> None:
    prob = _binary_positive_probability(
        [("happy", -2.0), ("non_happy", 2.0)],
        "happy",
        ["happy", "non_happy"],
    )
    assert prob == pytest.approx(0.119, abs=0.02)
