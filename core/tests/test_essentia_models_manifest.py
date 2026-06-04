from __future__ import annotations

from pathlib import Path

import yaml

MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "models_registry"
    / "essentia_models_manifest.yaml"
)


def _load() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_is_valid_yaml_with_required_sections() -> None:
    data = _load()
    assert isinstance(data, dict)
    assert "models" in data and isinstance(data["models"], dict)
    assert "profiles" in data and isinstance(data["profiles"], dict)
    assert data["license"]["name"] == "CC BY-NC-SA 4.0"


def test_model_urls_end_with_pb_or_json() -> None:
    data = _load()
    for key, entry in data["models"].items():
        assert entry["weights_url"].endswith(".pb"), key
        assert entry["metadata_url"].endswith(".json"), key
        assert entry["local_weights_path"].endswith(".pb"), key
        assert entry["local_metadata_path"].endswith(".json"), key


def test_profiles_reference_declared_models() -> None:
    data = _load()
    known = set(data["models"].keys())
    for profile, spec in data["profiles"].items():
        for model_key in spec.get("models", []):
            assert model_key in known, f"{profile}:{model_key}"


def test_phase6_minimal_excludes_maest() -> None:
    data = _load()
    minimal = data["profiles"]["phase6-minimal"]["models"]
    assert "discogs_maest_30s_pw_519l" not in minimal
    assert "genre_discogs519_maest_519l" not in minimal


def test_phase6_recommended_includes_maest_and_genre() -> None:
    data = _load()
    recommended = data["profiles"]["phase6-recommended"]
    assert recommended.get("extends") == "phase6-minimal"
    assert "discogs_maest_30s_pw_519l" in recommended["models"]
    assert "genre_discogs519_maest_519l" in recommended["models"]
