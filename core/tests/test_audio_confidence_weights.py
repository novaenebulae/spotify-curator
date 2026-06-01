from app.audio.confidence import compute_feature_confidence, source_quality_weight
from app.audio.essentia_aggregate import aggregate_segment_features
from app.audio.essentia_parser import ParsedSegmentFeatures


def test_deezer_only_lower_than_youtube_representative() -> None:
    deezer_only = aggregate_segment_features(
        [
            ParsedSegmentFeatures(
                bpm=120.0,
                bpm_confidence=0.9,
                source_quality="deezer_preview_30s",
                source_quality_weight=source_quality_weight("deezer_preview_30s"),
                match_confidence=0.85,
            )
        ],
        analysis_decision="deezer_preview_only_fallback",
    )
    youtube_two = aggregate_segment_features(
        [
            ParsedSegmentFeatures(
                bpm=120.0,
                bpm_confidence=0.9,
                source_quality="youtube_representative",
                source_quality_weight=source_quality_weight("youtube_representative"),
                match_confidence=0.9,
            ),
            ParsedSegmentFeatures(
                bpm=121.0,
                bpm_confidence=0.9,
                source_quality="youtube_representative",
                source_quality_weight=source_quality_weight("youtube_representative"),
                match_confidence=0.9,
            ),
        ],
        analysis_decision="deezer_preview_plus_two_youtube_segments",
    )
    assert deezer_only.feature_confidence is not None
    assert youtube_two.feature_confidence is not None
    assert deezer_only.feature_confidence < youtube_two.feature_confidence


def test_compute_feature_confidence_formula() -> None:
    c = compute_feature_confidence(
        [0.9, 0.8],
        source_quality_weights=[0.95, 1.0],
        match_confidences=[1.0, 0.9],
    )
    assert c is not None
    assert 0 < c <= 1
