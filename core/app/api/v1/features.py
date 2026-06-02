from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.features.coverage import FeatureCoverageService
from app.features.enrichment import ReccoBeatsEnrichmentService
from app.features.merge import FeatureMergeService
from app.features.schemas import (
    CoverageResponse,
    EnrichJobResponse,
    ReccoBeatsEnrichRequest,
    TrackFeaturesResponse,
)
from app.features.track_detail import TrackFeaturesService
from app.jobs.status_mapping import map_job_status

router = APIRouter(prefix="/features")
_enrichment = ReccoBeatsEnrichmentService()
_coverage = FeatureCoverageService()
_merge = FeatureMergeService()
_track_features = TrackFeaturesService()


class MergeRecomputeRequest(BaseModel):
    track_ids: list[int] | None = None
    limit: int = 5000


class MergeRecomputeResponse(BaseModel):
    tracks_processed: int
    deactivated_rows: int


@router.post("/reccobeats/enrich", response_model=EnrichJobResponse)
def start_reccobeats_enrichment(body: ReccoBeatsEnrichRequest) -> EnrichJobResponse:
    job_id = _enrichment.start_enrichment_job(
        track_ids=body.track_ids,
        filter_dict=body.filter,
        batch_size=body.batch_size,
        only_missing=body.only_missing,
        retry_failed=body.retry_failed,
        force_refresh=body.force_refresh,
        limit=body.limit,
    )
    return EnrichJobResponse(job_id=job_id, status=map_job_status("queued"))


@router.get("/tracks/{track_id}", response_model=TrackFeaturesResponse)
def get_track_features(track_id: int) -> TrackFeaturesResponse:
    engine = get_engine()
    with Session(engine) as session:
        return _track_features.get_track_features(session, track_id)


@router.get("/coverage", response_model=CoverageResponse)
def get_feature_coverage(
    source: str = Query(default="all"),
    include_failed: bool = Query(default=True),
    include_fields: bool = Query(default=True),
    recent_failures_limit: int = Query(default=20, ge=1, le=100),
    failures_page: int = Query(default=1, ge=1),
    failures_page_size: int = Query(default=20, ge=1, le=200),
) -> CoverageResponse:
    engine = get_engine()
    with Session(engine) as session:
        return _coverage.get_coverage(
            session,
            source=source,
            include_failed=include_failed,
            include_fields=include_fields,
            recent_failures_limit=recent_failures_limit,
            failures_page=failures_page,
            failures_page_size=failures_page_size,
        )


@router.post("/merge/recompute", response_model=MergeRecomputeResponse)
def recompute_feature_merge(body: MergeRecomputeRequest) -> MergeRecomputeResponse:
    engine = get_engine()
    with Session(engine) as session:
        stats = _merge.recompute(
            session,
            track_ids=body.track_ids,
            limit=body.limit,
        )
        session.commit()
    return MergeRecomputeResponse(
        tracks_processed=stats["tracks_processed"],
        deactivated_rows=stats["deactivated_rows"],
    )
