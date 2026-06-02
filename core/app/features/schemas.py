from __future__ import annotations

from pydantic import BaseModel, Field


class ReccoBeatsEnrichRequest(BaseModel):
    track_ids: list[int] | None = None
    filter: dict | None = None
    batch_size: int = Field(default=50, ge=1, le=500)
    only_missing: bool = True
    retry_failed: bool = False
    force_refresh: bool = False
    limit: int | None = Field(default=None, ge=1)


class EnrichJobResponse(BaseModel):
    job_id: str
    status: str


class CoverageFieldOut(BaseModel):
    field: str
    available_count: int
    coverage_percent: float


class CoverageSourceOut(BaseModel):
    source: str
    active: bool
    version: str | None
    track_count: int
    success_count: int
    missing_count: int
    failed_count: int
    not_found_count: int
    partial_count: int
    coverage_percent: float


class CoverageSummaryOut(BaseModel):
    track_count: int
    with_any_features: int
    with_reccobeats: int
    missing_reccobeats: int
    failed_reccobeats: int
    not_found_reccobeats: int = 0
    with_essentia_lowlevel: int = 0
    missing_essentia_lowlevel: int = 0
    failed_essentia_lowlevel: int = 0
    not_found_essentia_lowlevel: int = 0
    coverage_percent: float


class RecentFailureOut(BaseModel):
    id: str
    source: str | None = None
    track_id: int
    title: str
    artist_names: list[str]
    status: str
    error_code: str | None
    error_message: str | None
    occurred_at: str | None = None


class FailurePageOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RecentFailureOut]


class CoverageFieldsBySourceOut(BaseModel):
    reccobeats: list[CoverageFieldOut] = Field(default_factory=list)
    essentia_lowlevel: list[CoverageFieldOut] = Field(default_factory=list)


class CoverageResponse(BaseModel):
    summary: CoverageSummaryOut
    sources: list[CoverageSourceOut]
    fields: list[CoverageFieldOut]
    fields_by_source: CoverageFieldsBySourceOut | None = None
    recent_failures: list[RecentFailureOut]
    failures: FailurePageOut | None = None


class TrackFeatureMetaOut(BaseModel):
    pipeline_version: str | None = None
    segments_used: int | None = None
    segments_planned: int | None = None
    segments_analyzed: int | None = None
    segments_missing_reason: str | None = None
    analysis_decision: str | None = None
    external_track_id: str | None = None


class TrackFeatureMergedOut(BaseModel):
    primary_source: str
    display_name: str
    is_active: bool
    status: str
    feature_confidence: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    fields: dict[str, float | int] = Field(default_factory=dict)
    meta: TrackFeatureMetaOut = Field(default_factory=TrackFeatureMetaOut)
    fetched_at: str | None = None


class TrackFeatureSourceOut(BaseModel):
    source_name: str
    display_name: str
    is_active: bool
    status: str
    feature_confidence: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    fields: dict[str, float | int] = Field(default_factory=dict)
    extended: dict = Field(default_factory=dict)
    pipeline_version: str | None = None
    fetched_at: str | None = None


class TrackFeatureAvailabilityOut(BaseModel):
    has_any_features: bool
    has_reccobeats: bool
    has_essentia_lowlevel: bool
    other_sources_count: int = 0


class TrackFeaturesResponse(BaseModel):
    track_id: int
    merged: TrackFeatureMergedOut | None = None
    sources: list[TrackFeatureSourceOut] = Field(default_factory=list)
    availability: TrackFeatureAvailabilityOut
