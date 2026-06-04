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


def test_registry_phase6_aliases_resolve() -> None:
    reg = FeatureRegistry()
    expected = {
        "genre_discogs519": "genre_discogs_519",
        "mood_electronic": "electronic_profile_score",
        "mood_acoustic": "acoustic_profile_score",
        "acoustic": "acoustic_profile_score",
        "instrumental": "instrumental_focus_score",
        "valence_local": "valence_tf",
        "danceability_local": "danceability_tf",
    }
    for alias, canonical in expected.items():
        assert reg.is_known(alias)
        assert reg.resolve_name(alias) == canonical
        assert reg.get(alias) is not None


def test_registry_active_phase_makes_phase6_usable() -> None:
    reg = FeatureRegistry()
    assert reg.ACTIVE_PHASE == 6
    # Phase-6 features are consumable now (not "future"); phase-7 still future.
    assert not reg.is_future("mood_happy_score")
    assert not reg.is_future("vocal_presence_score")
    assert reg.is_future("mood_dark_score")
    assert reg.is_future("embedding_similarity")
