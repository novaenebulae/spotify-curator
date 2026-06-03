from __future__ import annotations

import json
from pathlib import Path

_PRESETS_PATH = Path(__file__).parent / "data" / "presets.json"


def load_presets() -> list[dict]:
    if not _PRESETS_PATH.exists():
        return [_default_dark_intense()]
    return json.loads(_PRESETS_PATH.read_text(encoding="utf-8"))


def _default_dark_intense() -> dict:
    return {
        "id": "dark_intense",
        "label": "Dark / Intense",
        "rule": {
            "name": "Dark / Intense",
            "target_size": 80,
            "engine_version": "playlist_engine_v1",
            "source": {"liked_tracks": True},
            "filters": {
                "features": {
                    "energy": {"min": 0.55, "required": True},
                    "valence": {"max": 0.6, "required": False},
                    "feature_confidence": {"min": 0.5, "required": True},
                },
                "availability_status": {"include": ["available", "unknown"]},
            },
            "weights": {
                "missing_component_behavior": "skip_and_renormalize",
                "components": {
                    "energy": {"weight": 0.25},
                    "valence_inverse": {"weight": 0.15},
                    "danceability": {"weight": 0.15},
                    "playlist_fit_score": {"weight": 0.2},
                    "diversity_bonus": {"weight": 0.15},
                    "freshness_score": {"weight": 0.1},
                },
            },
            "constraints": {
                "max_tracks_per_artist": 3,
                "max_tracks_per_album": 2,
                "avoid_duplicate_isrc": True,
            },
            "ordering": {"mode": "score_desc", "random_seed": 42},
            "spotify": {
                "playlist_name": "Dark / Intense",
                "visibility": "private",
                "sync_mode": "replace_after_dry_run",
            },
        },
    }
