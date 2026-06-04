from __future__ import annotations

from pydantic import BaseModel


class SegmentPlanRequest(BaseModel):
    track_id: int
    strategy: str = "hybrid_deezer_youtube_representative"
    analysis_mode: str = "fast"
    segment_duration_seconds: float | None = None
    youtube_available: bool | None = None
    youtube_confidence: float | None = None


class PlannedSegmentResponse(BaseModel):
    segment_type: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float


class SegmentPlanResponse(BaseModel):
    track_id: int
    duration_ms: int
    strategy: str
    analysis_decision: str | None = None
    segments: list[PlannedSegmentResponse]


class AudioDownloadRequest(BaseModel):
    track_ids: list[int] | None = None
    filter: dict | None = None
    strategy: str = "hybrid_deezer_youtube_representative"
    analysis_mode: str = "fast"
    segment_duration_seconds: float | None = None
    only_missing: bool = True
    retry_failed: bool = False
    limit: int | None = None
    provider: str = "ytdlp"


class AudioAnalysisRequest(BaseModel):
    track_ids: list[int] | None = None
    filter: dict | None = None
    analysis_mode: str = "fast"
    only_missing: bool = True
    retry_failed: bool = False
    force_refresh: bool = False
    limit: int | None = None
    cleanup_after: bool = True
    require_existing_segments: bool = True


class AdvancedAnalysisRequest(BaseModel):
    track_ids: list[int] | None = None
    filter: dict | None = None
    only_missing: bool = True
    force_refresh: bool = False
    retry_failed: bool = False
    limit: int | None = None
    analysis_mode: str = "fast"
    strategy: str | None = None
    segment_duration_seconds: float | None = None
    include_lowlevel: bool = True
    include_tensorflow: bool = True
    pipeline_mode: str = "streaming"
    model_profile: str = "phase6-recommended"
    require_real_tensorflow: bool = False


class AudioJobResponse(BaseModel):
    job_id: str
    status: str


class CacheCleanupRequest(BaseModel):
    dry_run: bool = True
    older_than_hours: int = 0
    include_failed: bool = False


class CacheCleanupResponse(BaseModel):
    dry_run: bool
    matched_files: int
    deleted_files: int
    freed_bytes: int
    errors: list[str]


class TrackSegmentView(BaseModel):
    id: int
    segment_type: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    source: str
    has_file: bool
    file_hash: str | None
    features_available: bool
    deleted_at: str | None
    created_at: str


class TrackSegmentsResponse(BaseModel):
    track_id: int
    segments: list[TrackSegmentView]
    cleanup: dict
