from __future__ import annotations

import random

from app.playlists.rule_schemas import PlaylistRule
from app.playlists.scoring import ScoreResult
from app.playlists.types import TrackFeatureView


def apply_ordering(
    rule: PlaylistRule,
    selected: list[ScoreResult],
    views: dict[int, TrackFeatureView],
) -> list[ScoreResult]:
    mode = rule.ordering.mode
    if mode == "score_desc":
        return sorted(selected, key=lambda s: (-s.final_score, s.track_id))
    if mode == "score_asc":
        return sorted(selected, key=lambda s: (s.final_score, s.track_id))
    if mode == "random_seeded":
        seed = rule.ordering.random_seed or 42
        rng = random.Random(seed)
        out = list(selected)
        rng.shuffle(out)
        return out
    if mode == "artist_grouped":
        return sorted(
            selected,
            key=lambda s: (
                (views[s.track_id].artist_names[0] if views[s.track_id].artist_names else ""),
                -s.final_score,
                s.track_id,
            ),
        )
    if mode == "artist_spread":
        return selected
    return sorted(selected, key=lambda s: (-s.final_score, s.track_id))
