from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.cleanup import AudioCleanupService
from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_ESSENTIA_LOWLEVEL,
)
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.audio.confidence import source_quality_weight
from app.audio.essentia_aggregate import aggregate_segment_features
from app.audio.essentia_parser import (
    parse_essentia_json_file,
    parsed_segment_from_features_json,
    parsed_segment_to_storage_dict,
)
from app.audio.essentia_runner import run_essentia_lowlevel
from app.audio.paths import segment_absolute_path
from app.database.engine import get_engine
from app.database.models_audio import AudioAnalysisJob
from app.database.repositories.audio_analysis_jobs import AudioAnalysisJobsRepository
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.features.upsert import FeatureUpsertService
from app.jobs.items.constants import WORKER_TYPE_ESSENTIA_LOWLEVEL
from app.jobs.items.service import ReservedJobItem
from app.settings.config import settings
from app.workers.base_worker import BaseWorker


class EssentiaLowlevelWorker(BaseWorker):
    worker_type = WORKER_TYPE_ESSENTIA_LOWLEVEL

    def __init__(
        self,
        *,
        run_essentia: object | None = None,
        parse_json: object | None = None,
    ) -> None:
        super().__init__()
        self._run_essentia = run_essentia or run_essentia_lowlevel
        self._parse_json = parse_json or parse_essentia_json_file
        self._segments = TrackSegmentsRepository()
        self._analysis = AudioAnalysisJobsRepository()
        self._upsert = FeatureUpsertService()
        self._cleanup = AudioCleanupService()

    def process_item(self, item: object) -> None:
        assert isinstance(item, ReservedJobItem)
        if item.track_id is None:
            self._items.mark_failed(
                item.id, error_code="INVALID_ITEM", error_message="Missing track_id"
            )
            return

        engine = get_engine()
        with Session(engine) as session:
            job = session.get(Job, item.job_id)
            job_item = session.get(JobItem, item.id)
        if (
            job is not None
            and job.job_type == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE
            and job_item is not None
            and job_item.stage_name == STAGE_ESSENTIA_LOWLEVEL
        ):
            self._process_pipeline_lowlevel_item(item, job_item)
            return

        inp = item.input_json
        cleanup_after = inp.get("cleanup_after", True)
        with Session(engine) as session:
            segments = self._segments.list_active_with_file(session, item.track_id)
        if not segments:
            self._items.mark_skipped(item.id, reason="No segments with audio files")
            return

        self._heartbeat_running(current_job_id=item.job_id, current_item_id=item.id)
        parsed_list = []
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        for seg in segments:
            self._heartbeat_running(current_job_id=item.job_id, current_item_id=item.id)
            wav = segment_absolute_path(seg.temporary_path or "")
            if not wav.is_file():
                continue
            with Session(engine) as session:
                aj = AudioAnalysisJob(
                    job_id=item.job_id,
                    track_id=item.track_id,
                    segment_id=seg.id,
                    analysis_level="essentia_lowlevel",
                    docker_service="essentia-lowlevel-worker",
                    image_name=settings.essentia_lowlevel_image,
                    image_tag=settings.essentia_lowlevel_image_tag,
                    pipeline_version=settings.essentia_lowlevel_pipeline_version,
                    input_path=seg.temporary_path,
                    status="running",
                    attempt_count=1,
                    created_at=now,
                    started_at=now,
                )
                self._analysis.insert(session, aj)
                session.commit()
                aj_id = aj.id

            try:
                if os.getenv("ESSENTIA_USE_FIXTURE_JSON"):
                    fixture = os.getenv("ESSENTIA_USE_FIXTURE_JSON")
                    out_path = fixture
                    rel_out = fixture
                else:
                    out_path, rel_out = self._run_essentia(
                        input_wav=wav,
                        track_id=item.track_id,
                        segment_id=seg.id,
                        job_id=item.job_id,
                    )
                parsed = self._parse_json(str(out_path))
                parsed.source_quality = seg.source_quality
                parsed.source_quality_weight = source_quality_weight(seg.source_quality)
                parsed.match_confidence = float(seg.confidence or 1.0)
                parsed_list.append(parsed)
                features_json = json.dumps(parsed.raw_summary)
                with Session(engine) as session:
                    self._segments.update_fields(
                        session,
                        seg.id,
                        features_json=features_json,
                        confidence=parsed.key_confidence or parsed.bpm_confidence,
                    )
                    row = self._analysis.get(session, aj_id)
                    if row:
                        row.status = "success"
                        row.output_path = rel_out
                        row.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
                    session.commit()
            except Exception as e:
                with Session(engine) as session:
                    row = self._analysis.get(session, aj_id)
                    if row:
                        row.status = "failed"
                        row.last_error = str(e)[:2000]
                        row.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
                    session.commit()
                raise

        if not parsed_list:
            self._items.mark_failed(
                item.id,
                error_code="NO_SEGMENTS_ANALYZED",
                error_message="No segments could be analyzed",
            )
            return

        analysis_decision = None
        segments_planned: int | None = None
        with Session(engine) as session:
            from app.database.repositories.audio_download_jobs import AudioDownloadJobsRepository

            dl = AudioDownloadJobsRepository().get_latest_for_track(session, item.track_id)
            if dl and dl.result_json:
                try:
                    data = json.loads(dl.result_json)
                    analysis_decision = data.get("analysis_decision")
                    sp = data.get("segments_planned")
                    if isinstance(sp, int):
                        segments_planned = sp
                except json.JSONDecodeError:
                    pass
        aggregated = aggregate_segment_features(
            parsed_list,
            analysis_decision=analysis_decision,
            segments_planned=segments_planned,
            segments_missing_reason="segment_download_or_file_missing"
            if segments_planned is not None and segments_planned > len(parsed_list)
            else None,
        )
        with Session(engine) as session:
            self._upsert.upsert_essentia_lowlevel(
                session,
                track_id=item.track_id,
                aggregated=aggregated,
                force_refresh=bool(inp.get("force_refresh")),
            )
            session.commit()

        if cleanup_after and not settings.audio_keep_segments_after_analysis:
            with Session(engine) as session:
                job = session.get(Job, item.job_id)
                is_pipeline_job = (
                    job is not None and job.job_type == JOB_TYPE_AUDIO_ANALYSIS_PIPELINE
                )
            if not is_pipeline_job:
                self._cleanup.cleanup_files(track_id=item.track_id)

        self._items.mark_success(
            item.id,
            result_json={
                "segments_analyzed": len(parsed_list),
                "bpm": aggregated.bpm,
                "pipeline_version": settings.essentia_lowlevel_pipeline_version,
            },
        )

    def _process_pipeline_lowlevel_item(
        self, item: ReservedJobItem, job_item: JobItem
    ) -> None:
        if item.segment_id is None:
            self._items.mark_failed(
                item.id,
                error_code="INVALID_ITEM",
                error_message="Pipeline low-level item missing segment_id",
            )
            return

        pipeline_version = (
            job_item.pipeline_version or settings.essentia_lowlevel_pipeline_version
        )
        engine = get_engine()
        with Session(engine) as session:
            seg = self._segments.get(session, item.segment_id)
        if seg is None or seg.deleted_at is not None:
            self._items.mark_skipped(item.id, reason="Segment not found or deleted")
            return

        wav = segment_absolute_path(seg.temporary_path or "")
        if not wav.is_file():
            self._items.mark_failed(
                item.id,
                error_code="SEGMENT_FILE_MISSING",
                error_message="Segment audio file not found",
            )
            return

        with Session(engine) as session:
            existing = self._analysis.get_latest_success_for_segment(
                session,
                segment_id=item.segment_id,
                pipeline_version=pipeline_version,
            )
        if existing is not None and seg.features_json:
            self._items.mark_success(
                item.id,
                result_json={
                    "segment_id": item.segment_id,
                    "pipeline_version": pipeline_version,
                    "idempotent": True,
                },
            )
            return

        if seg.features_json:
            try:
                parsed_segment_from_features_json(seg.features_json)
                self._items.mark_success(
                    item.id,
                    result_json={
                        "segment_id": item.segment_id,
                        "pipeline_version": pipeline_version,
                        "idempotent": True,
                        "source": "features_json",
                    },
                )
                return
            except (json.JSONDecodeError, ValueError):
                pass

        self._heartbeat_running(current_job_id=item.job_id, current_item_id=item.id)
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        with Session(engine) as session:
            aj = AudioAnalysisJob(
                job_id=item.job_id,
                track_id=item.track_id,
                segment_id=item.segment_id,
                analysis_level="essentia_lowlevel",
                docker_service="essentia-lowlevel-worker",
                image_name=settings.essentia_lowlevel_image,
                image_tag=settings.essentia_lowlevel_image_tag,
                pipeline_version=pipeline_version,
                input_path=seg.temporary_path,
                status="running",
                attempt_count=item.attempt_count,
                created_at=now,
                started_at=now,
            )
            self._analysis.insert(session, aj)
            session.commit()
            aj_id = aj.id

        try:
            if os.getenv("ESSENTIA_USE_FIXTURE_JSON"):
                fixture = os.getenv("ESSENTIA_USE_FIXTURE_JSON")
                out_path = fixture
                rel_out = fixture
            else:
                out_path, rel_out = self._run_essentia(
                    input_wav=wav,
                    track_id=item.track_id,
                    segment_id=item.segment_id,
                    job_id=item.job_id,
                )
            parsed = self._parse_json(str(out_path))
            parsed.source_quality = seg.source_quality
            parsed.source_quality_weight = source_quality_weight(seg.source_quality)
            parsed.match_confidence = float(seg.confidence or 1.0)
            features_json = json.dumps(parsed_segment_to_storage_dict(parsed))
            with Session(engine) as session:
                self._segments.update_fields(
                    session,
                    item.segment_id,
                    features_json=features_json,
                    confidence=parsed.key_confidence or parsed.bpm_confidence,
                )
                row = self._analysis.get(session, aj_id)
                if row:
                    row.status = "success"
                    row.output_path = rel_out
                    row.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
                session.commit()
        except Exception as e:
            with Session(engine) as session:
                row = self._analysis.get(session, aj_id)
                if row:
                    row.status = "failed"
                    row.last_error = str(e)[:2000]
                    row.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
                session.commit()
            retryable = "timeout" in str(e).lower()
            self._items.mark_failed(
                item.id,
                error_code="ESSENTIA_LOWLEVEL_FAILED",
                error_message=str(e)[:500],
                retryable=retryable,
            )
            return

        self._items.mark_success(
            item.id,
            result_json={
                "segment_id": item.segment_id,
                "pipeline_version": pipeline_version,
                "bpm": parsed.bpm,
            },
        )
