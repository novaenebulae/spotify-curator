from app.playlists.rule_validation import PlaylistRuleValidator
from app.playlists.presets import load_presets


def test_valid_rule_from_preset() -> None:
    preset = load_presets()[0]
    result = PlaylistRuleValidator().validate(rule=preset["rule"])
    assert result.valid is True
    assert result.normalized_rule is not None


def test_invalid_no_source() -> None:
    rule = dict(load_presets()[0]["rule"])
    rule["source"] = {
        "liked_tracks": False,
        "playlists_include": [],
        "track_ids_include": [],
    }
    result = PlaylistRuleValidator().validate(rule=rule)
    assert result.valid is False
    assert any(e.code == "NO_SOURCE_SELECTED" for e in result.errors)


def test_future_feature_warning() -> None:
    preset = next(p for p in load_presets() if p["id"] == "low_vocal_phase7")
    result = PlaylistRuleValidator().validate(rule=preset["rule"])
    assert result.valid is True
    assert any(w.code == "FEATURE_NOT_AVAILABLE_YET" for w in result.warnings)


def test_unknown_feature_error() -> None:
    rule = dict(load_presets()[0]["rule"])
    rule["filters"]["features"]["unknown_feature_xyz"] = {"min": 0.5}
    result = PlaylistRuleValidator().validate(rule=rule)
    assert result.valid is False
    assert any(e.code == "UNKNOWN_FILTER" for e in result.errors)
