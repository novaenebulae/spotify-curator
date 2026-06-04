from __future__ import annotations

from dataclasses import dataclass

# Bridge between the legacy output keys consumed by the aggregation layer
# (app/features/advanced/mappers.py, feature_aggregation.py) and the manifest
# model keys managed by ModelManager (phase 6.8A). The aggregation contract is
# kept on the legacy keys; only model availability/paths/labels are resolved
# through the manifest.

# Embeddings (Discogs EffNet).
EMBEDDINGS_LEGACY_KEY = "discogs_effnet_embeddings"
EMBEDDINGS_EXTRACTOR_KEY = "discogs_effnet_bs64"

# Genre (Genre Discogs519 head on top of MAEST embeddings).
GENRE_LEGACY_KEY = "genre_discogs_519"
GENRE_EXTRACTOR_KEY = "discogs_maest_30s_pw_519l"
GENRE_HEAD_KEY = "genre_discogs519_maest_519l"


@dataclass(frozen=True)
class ClassifierSpec:
    """Maps a legacy classifier output key to its manifest extractor + head."""

    legacy_key: str
    extractor_key: str
    head_key: str
    kind: str  # "binary" | "two_class" | "arousal_valence"
    positive_label: str | None = None


# Classifier heads riding on Discogs EffNet embeddings + arousal/valence
# (DEAM head on MusicNN embeddings, only present in phase6-full).
CLASSIFIER_SPECS: tuple[ClassifierSpec, ...] = (
    ClassifierSpec(
        legacy_key="mood_aggressive",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="mood_aggressive_discogs_effnet",
        kind="binary",
        positive_label="aggressive",
    ),
    ClassifierSpec(
        legacy_key="mood_happy",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="mood_happy_discogs_effnet",
        kind="binary",
        positive_label="happy",
    ),
    ClassifierSpec(
        legacy_key="mood_party",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="mood_party_discogs_effnet",
        kind="binary",
        positive_label="party",
    ),
    ClassifierSpec(
        legacy_key="mood_relaxed",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="mood_relaxed_discogs_effnet",
        kind="binary",
        positive_label="relaxed",
    ),
    ClassifierSpec(
        legacy_key="mood_sad",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="mood_sad_discogs_effnet",
        kind="binary",
        positive_label="sad",
    ),
    ClassifierSpec(
        legacy_key="mood_electronic",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="mood_electronic_discogs_effnet",
        kind="binary",
        positive_label="electronic",
    ),
    ClassifierSpec(
        legacy_key="mood_acoustic",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="mood_acoustic_discogs_effnet",
        kind="binary",
        positive_label="acoustic",
    ),
    ClassifierSpec(
        legacy_key="danceability",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="danceability_discogs_effnet",
        kind="binary",
        positive_label="danceable",
    ),
    ClassifierSpec(
        legacy_key="approachability",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="approachability_regression_discogs_effnet",
        kind="binary",
    ),
    ClassifierSpec(
        legacy_key="engagement",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="engagement_regression_discogs_effnet",
        kind="binary",
    ),
    ClassifierSpec(
        legacy_key="voice_instrumental",
        extractor_key=EMBEDDINGS_EXTRACTOR_KEY,
        head_key="voice_instrumental_discogs_effnet",
        kind="two_class",
        positive_label="voice",
    ),
    ClassifierSpec(
        legacy_key="arousal_valence",
        extractor_key="msd_musicnn",
        head_key="deam_msd_musicnn_2",
        kind="arousal_valence",
    ),
)


def classifier_specs() -> tuple[ClassifierSpec, ...]:
    return CLASSIFIER_SPECS
