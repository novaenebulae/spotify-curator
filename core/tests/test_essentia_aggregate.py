from __future__ import annotations

from app.audio.essentia_aggregate import aggregate_segment_features
from app.audio.essentia_parser import ParsedSegmentFeatures


def test_aggregate_median_bpm_and_key_vote() -> None:
    a = ParsedSegmentFeatures(bpm=120.0, key=0, mode=1, key_confidence=0.9, loudness=-10.0)
    b = ParsedSegmentFeatures(bpm=122.0, key=0, mode=1, key_confidence=0.8, loudness=-8.0)
    c = ParsedSegmentFeatures(bpm=121.0, key=2, mode=0, key_confidence=0.2, loudness=-9.0)
    agg = aggregate_segment_features([a, b, c])
    assert agg.bpm == 121.0
    assert agg.key == 0
    assert agg.mode == 1
    assert agg.segments_used == 3
