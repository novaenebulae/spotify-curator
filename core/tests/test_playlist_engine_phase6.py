"""Phase-6 full-consumption: the engine USES advanced features when present and
warns cleanly when they are missing/future (ACTIVE_PHASE=6)."""

from __future__ import annotations

from app.playlists.filters import apply_strict_filters
from app.playlists.rule_schemas import PlaylistRule
from app.playlists.scoring import score_tracks
from app.playlists.types import FeatureValue, TrackFeatureView


def _view(track_id: int, features: dict[str, FeatureValue]) -> TrackFeatureView:
    return TrackFeatureView(
        track_id=track_id,
        spotify_track_id=f"sp{track_id}",
        title=f"Track {track_id}",
        artist_names=["A"],
        artist_ids=[1],
        album_id=1,
        album_name="Album",
        isrc=f"isrc{track_id}",
        duration_ms=180000,
        availability_status="available",
        market_status="available",
        liked=True,
        playlist_ids=[],
        duplicate_status="unique",
        preview_available=True,
        features=features,
    )


def _available(name: str, value: float) -> FeatureValue:
    return FeatureValue(name=name, value=value, confidence=0.9, source="essentia_tensorflow",
                        status="available", model_name="m", pipeline_version="tf_v1")


def _rule(payload: dict) -> PlaylistRule:
    base = {
        "name": "Phase6",
        "target_size": 10,
        "engine_version": "playlist_engine_v1",
        "source": {"liked_tracks": True},
        "filters": {"features": {}},
        "weights": {"components": {}},
        "constraints": {},
        "ordering": {"mode": "score_desc"},
        "spotify": {"playlist_name": "Phase6", "sync_mode": "add_only"},
    }
    base.update(payload)
    return PlaylistRule.model_validate(base)


def test_phase6_feature_is_consumed_when_present() -> None:
    # mood_electronic is an alias of electronic_profile_score.
    view = _view(
        1,
        {
            "mood_happy_score": _available("mood_happy_score", 0.8),
            "electronic_profile_score": _available("electronic_profile_score", 0.7),
        },
    )
    rule = _rule(
        {
            "weights": {
                "components": {
                    "mood_happy_score": {"weight": 0.5},
                    "mood_electronic": {"weight": 0.5},
                }
            }
        }
    )
    results, warnings = score_tracks(rule, {1: view})
    assert len(results) == 1
    res = results[0]
    assert res.excluded is False
    comps = res.score_details["components"]
    assert comps["mood_happy_score"]["skipped"] is False
    assert comps["mood_electronic"]["skipped"] is False
    assert "FEATURE_NOT_AVAILABLE_YET" not in warnings
    assert res.final_score > 0.0


def test_phase6_feature_missing_warns_without_crash() -> None:
    view = _view(
        1,
        {"mood_happy_score": FeatureValue(name="mood_happy_score", status="missing",
                                          missing_reason="FEATURE_MISSING")},
    )
    # required=false -> kept with warning (not excluded).
    kept, exclusions, _ = apply_strict_filters(
        _rule({"filters": {"features": {"mood_happy_score": {"min": 0.5, "required": False}}}}),
        {1: view},
    )
    assert 1 in kept
    # required=true with the feature entirely absent -> excluded with FEATURE_MISSING.
    empty_view = _view(1, {})
    kept2, exclusions2, _ = apply_strict_filters(
        _rule({"filters": {"features": {"mood_happy_score": {"min": 0.5, "required": True}}}}),
        {1: empty_view},
    )
    assert 1 not in kept2
    assert any(
        r.code == "FEATURE_MISSING" for exc in exclusions2 for r in exc.reasons
    )


def test_phase7_feature_still_warns_not_available_yet() -> None:
    view = _view(
        1,
        {"mood_dark_score": FeatureValue(name="mood_dark_score", status="not_available_yet",
                                         missing_reason="FEATURE_NOT_AVAILABLE_YET")},
    )
    rule = _rule({"weights": {"components": {"mood_dark_score": {"weight": 1.0}}}})
    results, warnings = score_tracks(rule, {1: view})
    assert "FEATURE_NOT_AVAILABLE_YET" in warnings
    assert results[0].excluded is True
