from __future__ import annotations

from fastapi import APIRouter, Query

from app.database.engine import get_engine
from app.features.coverage import FeatureCoverageService
from app.features.enrichment import ReccoBeatsEnrichmentService
from app.features.schemas import CoverageResponse, EnrichJobResponse, ReccoBeatsEnrichRequest
from app.jobs.status_mapping import map_job_status

router = APIRouter(prefix="/features")
_enrichment = ReccoBeatsEnrichmentService()
_coverage = FeatureCoverageService()


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


@router.get("/coverage", response_model=CoverageResponse)
def get_feature_coverage(
    source: str = Query(default="reccobeats"),
    include_failed: bool = Query(default=True),
    include_fields: bool = Query(default=True),
    recent_failures_limit: int = Query(default=20, ge=1, le=100),
) -> CoverageResponse:
    from sqlalchemy.orm import Session

    engine = get_engine()
    with Session(engine) as session:
        return _coverage.get_coverage(
            session,
            source=source,
            include_failed=include_failed,
            include_fields=include_fields,
            recent_failures_limit=recent_failures_limit,
        )
