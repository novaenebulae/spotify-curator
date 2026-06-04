from app.playlists.feature_registry import FeatureRegistry


def test_registry_resolves_known_feature() -> None:
    reg = FeatureRegistry()
    assert reg.get("energy") is not None
    assert reg.is_known("energy")


def test_registry_resolves_alias() -> None:
    reg = FeatureRegistry()
    assert reg.resolve_name("tempo") == "bpm"
    assert reg.get("tempo") is not None


def test_registry_rejects_unknown() -> None:
    reg = FeatureRegistry()
    assert not reg.is_known("not_a_real_feature_xyz")


def test_registry_marks_future_feature() -> None:
    reg = FeatureRegistry()
    assert reg.is_future("mood_dark_score")
    assert not reg.is_available_in_phase("mood_dark_score", phase=5)


def test_registry_phase6_advanced_features() -> None:
    reg = FeatureRegistry()
    assert reg.is_known("approachability")
    assert reg.is_known("energy_proxy")
    assert reg.is_known("danceability_tf")
    assert reg.is_available_in_phase("mood_happy_score", phase=6)
    assert not reg.is_available_in_phase("mood_happy_score", phase=5)


def test_registry_phase6_embedding_features() -> None:
    reg = FeatureRegistry()
    assert reg.is_known("style_embedding")
    assert reg.is_known("genre_discogs_519_top_k")
    assert reg.is_available_in_phase("timbre_embedding", phase=6)
