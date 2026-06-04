# ruff: noqa: E501
from __future__ import annotations

from app.playlists.types import FeatureDescriptor

_PHASE5_FEATURES: tuple[FeatureDescriptor, ...] = (
    FeatureDescriptor("bpm", "BPM", "float", 0.0, 300.0, ("reccobeats", "essentia_lowlevel"), phase_available=5),
    FeatureDescriptor(
        "energy", "Energy", "float", 0.0, 1.0, ("reccobeats", "essentia_lowlevel"), phase_available=5
    ),
    FeatureDescriptor("valence", "Valence", "float", 0.0, 1.0, ("reccobeats",), phase_available=5),
    FeatureDescriptor("danceability", "Danceability", "float", 0.0, 1.0, ("reccobeats",), phase_available=5),
    FeatureDescriptor("acousticness", "Acousticness", "float", 0.0, 1.0, ("reccobeats",), phase_available=5),
    FeatureDescriptor(
        "instrumentalness", "Instrumentalness", "float", 0.0, 1.0, ("reccobeats",), phase_available=5
    ),
    FeatureDescriptor("speechiness", "Speechiness", "float", 0.0, 1.0, ("reccobeats",), phase_available=5),
    FeatureDescriptor("liveness", "Liveness", "float", 0.0, 1.0, ("reccobeats",), phase_available=5),
    FeatureDescriptor("loudness", "Loudness", "float", -60.0, 0.0, ("reccobeats", "essentia_lowlevel"), phase_available=5),
    FeatureDescriptor("key", "Key", "int", 0.0, 11.0, ("reccobeats", "essentia_lowlevel"), phase_available=5),
    FeatureDescriptor("mode", "Mode", "int", 0.0, 1.0, ("reccobeats", "essentia_lowlevel"), phase_available=5),
    FeatureDescriptor("time_signature", "Time signature", "int", 0.0, 12.0, ("reccobeats",), phase_available=5),
    FeatureDescriptor("duration_ms", "Duration (ms)", "int", 0.0, None, ("reccobeats", "metadata"), phase_available=5),
    FeatureDescriptor(
        "feature_confidence",
        "Feature confidence",
        "float",
        0.0,
        1.0,
        ("reccobeats", "essentia_lowlevel"),
        phase_available=5,
    ),
    FeatureDescriptor("preview_available", "Preview available", "bool", phase_available=5, available_sources=("track_previews",)),
    FeatureDescriptor(
        "availability_status",
        "Availability",
        "string",
        phase_available=5,
        available_sources=("metadata",),
    ),
    FeatureDescriptor("market_status", "Market status", "string", phase_available=5, available_sources=("metadata",)),
    FeatureDescriptor("liked_status", "Liked", "bool", phase_available=5, available_sources=("metadata",)),
    FeatureDescriptor(
        "playlist_membership",
        "Playlist membership",
        "list",
        phase_available=5,
        available_sources=("metadata",),
    ),
    FeatureDescriptor("duplicate_status", "Duplicate status", "string", phase_available=5, available_sources=("metadata",)),
    FeatureDescriptor("isrc", "ISRC", "string", phase_available=5, available_sources=("metadata",)),
    FeatureDescriptor("artist_id", "Primary artist id", "int", phase_available=5, available_sources=("metadata",)),
    FeatureDescriptor("album_id", "Album id", "int", phase_available=5, available_sources=("metadata",)),
    FeatureDescriptor(
        "freshness_score",
        "Freshness",
        "float",
        0.0,
        1.0,
        available_sources=("derived",),
        phase_available=5,
    ),
    FeatureDescriptor(
        "playlist_fit_score",
        "Playlist fit",
        "float",
        0.0,
        1.0,
        available_sources=("derived",),
        phase_available=5,
    ),
    FeatureDescriptor(
        "diversity_bonus",
        "Diversity bonus",
        "float",
        0.0,
        1.0,
        available_sources=("derived",),
        phase_available=5,
    ),
    FeatureDescriptor(
        "preview_bonus",
        "Preview bonus",
        "float",
        0.0,
        1.0,
        available_sources=("derived",),
        phase_available=5,
    ),
)

_PHASE6_ADVANCED_FEATURES: tuple[FeatureDescriptor, ...] = (
    FeatureDescriptor(
        "approachability",
        "Approachability",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "engagement",
        "Engagement",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "mood_happy_score",
        "Happy mood",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "mood_sad_score",
        "Sad mood",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "mood_aggressive_score",
        "Aggressive mood",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "mood_relaxed_score",
        "Relaxed mood",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "mood_party_score",
        "Party mood",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "arousal",
        "Arousal",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "valence_tf",
        "Valence (TF)",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "danceability_tf",
        "Danceability (TF)",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "voice_probability",
        "Voice probability",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "vocal_presence_score",
        "Vocal presence",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "instrumental_focus_score",
        "Instrumental focus",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow", "derived"),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "acoustic_profile_score",
        "Acoustic profile",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "electronic_profile_score",
        "Electronic profile",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "energy_proxy",
        "Energy proxy",
        "float",
        0.0,
        1.0,
        ("derived", "essentia_lowlevel"),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
)

_PHASE6_EMBEDDING_FEATURES: tuple[FeatureDescriptor, ...] = (
    FeatureDescriptor(
        "style_embedding",
        "Style embedding",
        "vector",
        phase_available=6,
        available_sources=("track_embeddings",),
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "timbre_embedding",
        "Timbre embedding",
        "vector",
        phase_available=6,
        available_sources=("track_embeddings",),
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "genre_discogs_519",
        "Genre Discogs519",
        "list",
        phase_available=6,
        available_sources=("essentia_tensorflow",),
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "genre_discogs_519_top_label",
        "Genre top label",
        "string",
        phase_available=6,
        available_sources=("essentia_tensorflow",),
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "genre_discogs_519_top_score",
        "Genre top score",
        "float",
        0.0,
        1.0,
        ("essentia_tensorflow",),
        phase_available=6,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "genre_discogs_519_top_k",
        "Genre top-k",
        "list",
        phase_available=6,
        available_sources=("essentia_tensorflow",),
        missing_policy="warn_until_available",
    ),
)

_PHASE7_FEATURES: tuple[FeatureDescriptor, ...] = (
    FeatureDescriptor(
        "embedding_similarity",
        "Embedding similarity",
        "float",
        0.0,
        1.0,
        future_sources=("track_embeddings",),
        phase_available=7,
        missing_policy="warn_until_available",
    ),
    FeatureDescriptor(
        "mood_dark_score",
        "Dark mood",
        "float",
        0.0,
        1.0,
        future_sources=("essentia_tensorflow", "derived"),
        phase_available=7,
        missing_policy="warn_until_available",
    ),
)

_ALL_DESCRIPTORS = (
    _PHASE5_FEATURES + _PHASE6_ADVANCED_FEATURES + _PHASE6_EMBEDDING_FEATURES + _PHASE7_FEATURES
)

_ALIASES: dict[str, str] = {
    "tempo": "bpm",
    # Phase 6 advanced-feature aliases (see docs/18 section 3.6).
    "genre_discogs519": "genre_discogs_519",
    "mood_electronic": "electronic_profile_score",
    "mood_acoustic": "acoustic_profile_score",
    "acoustic": "acoustic_profile_score",
    "instrumental": "instrumental_focus_score",
    "valence_local": "valence_tf",
    "danceability_local": "danceability_tf",
}

# Scoring-only alias resolved at score time, not a stored feature row.
_SCORING_ALIASES: dict[str, str] = {
    "valence_inverse": "valence",
}


class FeatureRegistry:
    """Canonical feature descriptors for playlist engine and clustering."""

    ENGINE_VERSION = "playlist_engine_v1"

    # Most advanced phase whose features have a real producer. Consumers treat
    # features with phase_available <= ACTIVE_PHASE as usable; beyond it warns
    # FEATURE_NOT_AVAILABLE_YET. Advance this as phases 7 (clustering) / 8 land.
    ACTIVE_PHASE = 6

    def __init__(self) -> None:
        self._by_name: dict[str, FeatureDescriptor] = {}
        for d in _ALL_DESCRIPTORS:
            self._by_name[d.name] = d
        for alias, canonical in {**_ALIASES, **_SCORING_ALIASES}.items():
            base = self._by_name.get(canonical)
            if base is None:
                continue
            self._by_name[alias] = FeatureDescriptor(
                name=alias,
                label=base.label,
                value_type=base.value_type,
                range_min=base.range_min,
                range_max=base.range_max,
                available_sources=base.available_sources + ("derived",),
                future_sources=base.future_sources,
                phase_available=base.phase_available,
                normalization=base.normalization,
                missing_policy=base.missing_policy,
                is_alias=True,
                alias_of=canonical,
            )

    def resolve_name(self, name: str) -> str:
        desc = self._by_name.get(name)
        if desc is None:
            return name
        if desc.is_alias and desc.alias_of:
            return desc.alias_of
        return name

    def get(self, name: str) -> FeatureDescriptor | None:
        canonical = self.resolve_name(name)
        return self._by_name.get(canonical)

    def is_known(self, name: str) -> bool:
        if name in self._by_name:
            return True
        return self.resolve_name(name) in {d.name for d in _ALL_DESCRIPTORS}

    def is_available_in_phase(self, name: str, *, phase: int | None = None) -> bool:
        desc = self.get(name)
        if desc is None:
            return False
        target = self.ACTIVE_PHASE if phase is None else phase
        return desc.phase_available <= target and not desc.is_alias

    def is_future(self, name: str, *, phase: int | None = None) -> bool:
        desc = self.get(name)
        if desc is None:
            return False
        target = self.ACTIVE_PHASE if phase is None else phase
        return desc.phase_available > target

    def list_all_descriptors(self) -> list[FeatureDescriptor]:
        out: list[FeatureDescriptor] = []
        seen: set[str] = set()
        for d in _ALL_DESCRIPTORS:
            if d.name in seen:
                continue
            seen.add(d.name)
            out.append(d)
        return out

    def list_descriptors(self, *, phase: int = 5) -> list[FeatureDescriptor]:
        out: list[FeatureDescriptor] = []
        seen: set[str] = set()
        for d in _ALL_DESCRIPTORS:
            if d.name in seen:
                continue
            if d.phase_available > phase:
                continue
            seen.add(d.name)
            out.append(d)
        return out

    def unknown_feature_error(self, name: str) -> str:
        return f"Unknown feature: {name}"


_default_registry: FeatureRegistry | None = None


def get_feature_registry() -> FeatureRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = FeatureRegistry()
    return _default_registry
