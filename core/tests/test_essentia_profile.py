from __future__ import annotations

from pathlib import Path

import yaml


def test_essentia_lowlevel_profile_uses_music_extractor_format() -> None:
    profile = Path(__file__).resolve().parents[2] / "profiles" / "essentia_lowlevel_basic.yaml"
    data = yaml.safe_load(profile.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "algorithms" not in data
    assert data.get("outputFormat") == "json"
    assert data.get("endTime") == 30
    assert data.get("highlevel", {}).get("compute") == 0
    assert "algorithms" not in data
