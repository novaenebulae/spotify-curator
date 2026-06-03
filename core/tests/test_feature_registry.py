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
