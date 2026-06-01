from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.cleanup import AudioCleanupService
from app.audio.confidence import source_quality_weight
from app.audio.essentia_aggregate import aggregate_segment_features
from app.audio.essentia_parser import parse_essentia_json_file
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
        inp = item.input_json
        cleanup_after = inp.get("cleanup_after", True)
        engine = get_engine()
        with Session(engine) as session:
            segments = self._segments.list_active_with_file(session, item.track_id)
        if not segments:
            self._items.mark_skipped(item.id, reason="No segments with audio files")
            return

        parsed_list = []
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        for seg in segments:
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
        with Session(engine) as session:
            from app.database.repositories.audio_download_jobs import AudioDownloadJobsRepository

            dl = AudioDownloadJobsRepository().get_latest_for_track(session, item.track_id)
            if dl and dl.result_json:
                try:
                    data = json.loads(dl.result_json)
                    analysis_decision = data.get("analysis_decision")
                except json.JSONDecodeError:
                    pass
        aggregated = aggregate_segment_features(
            parsed_list, analysis_decision=analysis_decision
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
            self._cleanup.cleanup_files(track_id=item.track_id)

        self._items.mark_success(
            item.id,
            result_json={
                "segments_analyzed": len(parsed_list),
                "bpm": aggregated.bpm,
                "pipeline_version": settings.essentia_lowlevel_pipeline_version,
            },
        )
