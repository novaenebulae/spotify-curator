from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.audio.hybrid_availability import HybridAvailabilityService
from app.audio.pipeline.constants import PIPELINE_MODE_STREAMING
from app.audio.pipeline.orchestrator import AnalysisPipelineOrchestrator, TrackSegmentPlan
from app.audio.provider import PlannedSegment
from app.audio.segments import plan_hybrid_for_track, plan_segments_for_track
from app.audio.track_context import load_track_context
from app.audio.track_selection import AudioTrackSelectionService
from app.database.engine import get_engine
from app.models_registry import ModelManager, ModelManagerError
from app.observability.errors import ApiError
from app.settings.config import settings


def _planned_segment_to_dict(seg: PlannedSegment) -> dict[str, Any]:
    return {
        "segment_type": seg.segment_type,
        "start_seconds": seg.start_seconds,
        "end_seconds": seg.end_seconds,
        "duration_seconds": seg.duration_seconds,
        "strategy": seg.strategy,
        "source": seg.source,
        "source_quality": seg.source_quality,
        "match_confidence": seg.match_confidence,
        "analysis_decision": seg.analysis_decision,
    }


def _profile_inference_ready(manager: ModelManager, profile: str) -> bool:
    status = manager.get_status()
    for row in status.get("profiles", []):
        if row.get("name") == profile:
            return row.get("status") == "available"
    return False


class AdvancedAnalysisJobService:
    def __init__(
        self,
        *,
        selection: AudioTrackSelectionService | None = None,
        orchestrator: AnalysisPipelineOrchestrator | None = None,
        hybrid: HybridAvailabilityService | None = None,
    ) -> None:
        self._selection = selection or AudioTrackSelectionService()
        self._orchestrator = orchestrator or AnalysisPipelineOrchestrator()
        self._hybrid = hybrid or HybridAvailabilityService()

    def start_advanced_analysis_job(
        self,
        *,
        track_ids: list[int] | None = None,
        filter_dict: dict[str, Any] | None = None,
        only_missing: bool = True,
        force_refresh: bool = False,
        retry_failed: bool = False,
        limit: int | None = None,
        strategy: str | None = None,
        analysis_mode: str = "fast",
        segment_duration_seconds: float | None = None,
        include_lowlevel: bool = True,
        include_tensorflow: bool = True,
        pipeline_mode: str = PIPELINE_MODE_STREAMING,
        model_profile: str = "phase6-recommended",
        require_real_tensorflow: bool = False,
    ) -> str:
        if include_tensorflow and require_real_tensorflow:
            try:
                manager = ModelManager()
            except ModelManagerError as exc:
                raise ApiError(
                    code=exc.code,
                    message=exc.message,
                    status_code=exc.status_code,
                    details=exc.details,
                ) from exc
            if not _profile_inference_ready(manager, model_profile):
                raise ApiError(
                    code="MODEL_MISSING",
                    message=f"Model profile {model_profile!r} is not fully available for real inference.",
                    status_code=409,
                )

        effective_only_missing = only_missing and not force_refresh
        seg_strategy = strategy or settings.audio_segment_strategy

        engine = get_engine()
        with Session(engine) as session:
            ids = self._selection.resolve_for_download(
                session,
                track_ids=track_ids,
                filter_dict=filter_dict,
                only_missing=effective_only_missing,
                retry_failed=retry_failed,
                limit=limit,
            )
            if not ids:
                raise ApiError(
                    code="NO_TRACKS",
                    message="No tracks matched the selection criteria.",
                    status_code=400,
                )

            track_plans: list[TrackSegmentPlan] = []
            for tid in ids:
                ctx = load_track_context(session, tid)
                if seg_strategy == "hybrid_deezer_youtube_representative":
                    deezer_ok, deezer_conf = self._hybrid.deezer_for_analysis(session, tid)
                    planned, _decision = plan_hybrid_for_track(
                        ctx,
                        analysis_mode=analysis_mode,
                        segment_duration_seconds=segment_duration_seconds,
                        deezer_preview_available=deezer_ok,
                        youtube_available=True,
                        deezer_match_confidence=deezer_conf,
                    )
                else:
                    planned = plan_segments_for_track(
                        ctx,
                        seg_strategy,
                        analysis_mode=analysis_mode,
                        segment_duration_seconds=segment_duration_seconds,
                    )
                planned_dicts = tuple(_planned_segment_to_dict(s) for s in planned)
                track_plans.append(
                    TrackSegmentPlan(
                        track_id=tid,
                        segment_ids=[None] * len(planned),
                        planned_segments=planned_dicts,
                    )
                )

        return self._orchestrator.create_pipeline_job(
            track_plans,
            include_lowlevel=include_lowlevel,
            include_tensorflow=include_tensorflow,
            pipeline_mode=pipeline_mode,
            input_payload={
                "strategy": seg_strategy,
                "analysis_mode": analysis_mode,
                "model_profile": model_profile,
                "require_real_tensorflow": require_real_tensorflow,
                "force_refresh": force_refresh,
            },
        )
