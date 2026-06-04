from __future__ import annotations

import json

from app.features.embeddings.genre_discogs import (
    GenreLabelScore,
    aggregate_genre_top_k,
    genre_features_from_top_k,
    parse_genre_segment_output,
)


def test_parse_genre_segment_output() -> None:
    payload = {"top_k": [{"label": "Techno", "score": 0.8}, {"label": "House", "score": 0.2}]}
    parsed = parse_genre_segment_output(payload)
    assert len(parsed) == 2
    assert parsed[0].label == "Techno"


def test_aggregate_genre_median_across_segments() -> None:
    seg1 = [GenreLabelScore("Techno", 0.9), GenreLabelScore("House", 0.1)]
    seg2 = [GenreLabelScore("Techno", 0.5), GenreLabelScore("House", 0.5)]
    agg = aggregate_genre_top_k([seg1, seg2])
    assert agg is not None
    assert agg.top_label == "Techno"
    assert agg.top_score == 0.7


def test_genre_features_from_top_k() -> None:
    agg = aggregate_genre_top_k(
        [[GenreLabelScore("Ambient", 0.6)], [GenreLabelScore("Ambient", 0.4)]]
    )
    assert agg is not None
    rows = genre_features_from_top_k(
        agg, model_name="genre_model", pipeline_version="tf_v1"
    )
    names = {r["feature_name"] for r in rows}
    assert "genre_discogs_519_top_label" in names
    assert "genre_discogs_519_top_score" in names
    top_row = next(r for r in rows if r["feature_name"] == "genre_discogs_519")
    data = json.loads(top_row["value_json"])
    assert isinstance(data, list)
