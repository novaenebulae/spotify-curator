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
    partial_count: int
    coverage_percent: float


class CoverageSummaryOut(BaseModel):
    track_count: int
    with_any_features: int
    with_reccobeats: int
    missing_reccobeats: int
    failed_reccobeats: int
    coverage_percent: float


class RecentFailureOut(BaseModel):
    track_id: int
    title: str
    artist_names: list[str]
    status: str
    error_code: str | None
    error_message: str | None


class CoverageResponse(BaseModel):
    summary: CoverageSummaryOut
    sources: list[CoverageSourceOut]
    fields: list[CoverageFieldOut]
    recent_failures: list[RecentFailureOut]
