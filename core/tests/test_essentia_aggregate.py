from __future__ import annotations

import json
from pathlib import Path

from app.audio.essentia_aggregate import aggregate_segment_features
from app.audio.essentia_parser import ParsedSegmentFeatures, parse_essentia_json


def test_aggregate_median_bpm_and_key_vote() -> None:
    a = ParsedSegmentFeatures(bpm=120.0, key=0, mode=1, key_confidence=0.9, loudness=-10.0)
    b = ParsedSegmentFeatures(bpm=122.0, key=0, mode=1, key_confidence=0.8, loudness=-8.0)
    c = ParsedSegmentFeatures(bpm=121.0, key=2, mode=0, key_confidence=0.2, loudness=-9.0)
    agg = aggregate_segment_features([a, b, c])
    assert agg.bpm == 121.0
    assert agg.key == 0
    assert agg.mode == 1
    assert agg.segments_used == 3


def test_aggregate_detail_json_includes_spectral_and_timbre() -> None:
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_sample.json"
    parsed = parse_essentia_json(json.loads(fixture.read_text(encoding="utf-8")))
    agg = aggregate_segment_features(
        [parsed],
        analysis_decision="deezer_only",
        segments_planned=1,
    )
    detail = agg.detail_json
    assert detail["spectral_centroid"] == 2200.0
    assert detail["spectral_rolloff"] == 4500.0
    assert detail["spectral_contrast"] == [1.0, 2.0, 3.0]
    assert detail["dynamic_complexity"] == 4.5
    assert detail["onset_rate"] == 2.1
    assert len(detail["mfcc"]) == 5
    assert len(detail["hpcp"]) == 3
    assert detail["analysis_decision"] == "deezer_only"
