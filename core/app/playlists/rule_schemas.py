from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

OrderingMode = Literal[
    "score_desc",
    "score_asc",
    "recently_added_desc",
    "recently_added_asc",
    "artist_grouped",
    "artist_spread",
    "random_seeded",
]

SyncMode = Literal[
    "create",
    "replace",
    "add_only",
    "remove_obsolete",
    "replace_after_dry_run",
]

FUTURE_ORDERING_MODES = frozenset(
    {
        "energy_curve_progressive",
        "warmup_peak_cooldown",
        "harmonic_flow",
        "cluster_walk",
        "embedding_similarity_path",
    }
)


class FeatureFilterSpec(BaseModel):
    min: float | None = None
    max: float | None = None
    required: bool = False
    unavailable_behavior: Literal["warn", "exclude", "skip_and_renormalize"] | None = None


class PlaylistRuleSource(BaseModel):
    liked_tracks: bool = False
    playlists_include: list[int] = Field(default_factory=list)
    playlists_exclude: list[int] = Field(default_factory=list)
    track_ids_include: list[int] = Field(default_factory=list)
    track_ids_exclude: list[int] = Field(default_factory=list)
    clusters_include: list[int] = Field(default_factory=list)
    clusters_exclude: list[int] = Field(default_factory=list)
    seed_tracks: list[str] = Field(default_factory=list)


class PlaylistRuleFilters(BaseModel):
    features: dict[str, FeatureFilterSpec] = Field(default_factory=dict)
    availability_status: dict[str, list[str]] | None = None
    market_status: dict[str, list[str]] | None = None
    exclude_artists: list[int] = Field(default_factory=list)
    exclude_albums: list[int] = Field(default_factory=list)
    exclude_tags: list[str] = Field(default_factory=list)


class WeightComponentSpec(BaseModel):
    weight: float = 0.0
    unavailable_behavior: Literal["warn", "skip_and_renormalize"] | None = None


class PlaylistRuleWeights(BaseModel):
    missing_component_behavior: Literal["skip_and_renormalize", "fail"] = "skip_and_renormalize"
    components: dict[str, WeightComponentSpec] = Field(default_factory=dict)


class ClusterDiversitySpec(BaseModel):
    enabled: bool = False


class VocalBalanceSpec(BaseModel):
    enabled: bool = False


class PlaylistRuleConstraints(BaseModel):
    max_tracks_per_artist: int | None = None
    max_tracks_per_album: int | None = None
    avoid_duplicate_isrc: bool = True
    avoid_same_artist_consecutive: bool = False
    cluster_diversity: ClusterDiversitySpec = Field(default_factory=ClusterDiversitySpec)
    vocal_balance: VocalBalanceSpec = Field(default_factory=VocalBalanceSpec)


class PlaylistRuleOrdering(BaseModel):
    mode: OrderingMode = "score_desc"
    random_seed: int | None = 42


class PlaylistRuleSpotify(BaseModel):
    playlist_name: str = ""
    visibility: Literal["public", "private", "collaborative"] = "private"
    sync_mode: SyncMode = "replace_after_dry_run"
    target_playlist_id: str | None = None


class PlaylistRule(BaseModel):
    name: str
    description: str | None = None
    target_size: int = 80
    engine_version: str = "playlist_engine_v1"
    source: PlaylistRuleSource
    filters: PlaylistRuleFilters
    weights: PlaylistRuleWeights
    constraints: PlaylistRuleConstraints
    ordering: PlaylistRuleOrdering
    spotify: PlaylistRuleSpotify

    @model_validator(mode="after")
    def _validate_target_size(self) -> PlaylistRule:
        if self.target_size <= 0 or self.target_size > 500:
            raise ValueError("TARGET_SIZE_INVALID")
        return self

    def model_dump_normalized(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PlaylistRuleValidateRequest(BaseModel):
    rule: dict[str, Any] | None = None
    rule_yaml: str | None = None


class ValidationIssue(BaseModel):
    code: str
    message: str
    path: str | None = None


class PlaylistRuleValidateResponse(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    normalized_rule: dict[str, Any] | None = None
