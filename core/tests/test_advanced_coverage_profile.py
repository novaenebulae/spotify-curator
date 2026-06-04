from __future__ import annotations

from app.features.advanced_coverage import advanced_coverage_feature_names


def test_recommended_profile_omits_arousal_valence_from_coverage() -> None:
    names = advanced_coverage_feature_names()
    assert "arousal" not in names
    assert "valence_tf" not in names
    assert "genre_discogs_519" in names
