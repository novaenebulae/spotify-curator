from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.deezer_preview_download import download_deezer_preview_segment
from app.audio.errors import LOCAL_ANALYSIS_UNAVAILABLE
from app.audio.hybrid_availability import HybridAvailabilityService
from app.audio.segments import plan_hybrid_for_track, plan_segments_for_track
from app.audio.strategy.hybrid import ANALYSIS_UNAVAILABLE
from app.audio.track_context import load_track_context
from app.audio.ytdlp_provider import YtDlpSegmentProvider, source_url_hash
from app.database.engine import get_engine
from app.database.models_audio import AudioDownloadJob, TrackSegment
from app.database.repositories.audio_download_jobs import AudioDownloadJobsRepository
from app.database.repositories.track_previews import TrackPreviewsRepository
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_SEGMENT_DOWNLOAD,
)
from app.audio.pipeline.handoff import PipelineSegmentHandoffService
from app.audio.pipeline.segment_download import (
    create_audio_download_job_row,
    download_planned_segment,
    planned_segment_from_dict,
)
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.jobs.items.constants import WORKER_TYPE_AUDIO_DOWNLOADER
from app.jobs.items.service import ReservedJobItem
from app.observability.redact import redact_dict
from app.previews.deezer_preview_refresh import ensure_fresh_deezer_preview_url
from app.settings.config import settings
from app.workers.base_worker import BaseWorker


class AudioDownloaderWorker(BaseWorker):
    worker_type = WORKER_TYPE_AUDIO_DOWNLOADER

    def __init__(
        self,
        *,
        provider: YtDlpSegmentProvider | None = None,
        use_test_provider: bool | None = None,
        availability: HybridAvailabilityService | None = None,
        previews_repo: TrackPreviewsRepository | None = None,
    ) -> None:
        super().__init__()
        if use_test_provider is None:
            use_test_provider = os.getenv("AUDIO_USE_TEST_PROVIDER", "").lower() in (
                "1",
                "true",
                "yes",
            )
        if use_test_provider:
            from app.audio.test_provider import StubAudioProvider

            self._provider = StubAudioProvider()
            self._is_test = True
        else:
            self._provider = provider or YtDlpSegmentProvider()
            self._is_test = False
        self._downloads = AudioDownloadJobsRepository()
        self._segments = TrackSegmentsRepository()
        self._availability = availability or HybridAvailabilityService()
        self._previews = previews_repo or TrackPreviewsRepository()
        self._handoff = PipelineSegmentHandoffService()

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
            and job_item.stage_name == STAGE_SEGMENT_DOWNLOAD
        ):
            self._process_pipeline_segment_download(item)
            return

        with Session(engine) as session:
            ctx = load_track_context(session, item.track_id)
        inp = item.input_json
        strategy = inp.get("strategy", settings.audio_segment_strategy)
        analysis_mode = inp.get("analysis_mode", "fast")
        seg_dur = inp.get("segment_duration_seconds")

        now = datetime.now(tz=UTC).replace(tzinfo=None)
        with Session(engine) as session:
            dl_row = AudioDownloadJob(
                job_id=item.job_id,
                track_id=item.track_id,
                provider=inp.get("provider", "ytdlp"),
                status="running",
                attempt_count=item.attempt_count,
                max_attempts=settings.audio_download_max_retries,
                rate_limited=False,
                created_at=now,
                started_at=now,
            )
            self._downloads.insert(session, dl_row)
            session.commit()
            download_id = dl_row.id

        try:
            analysis_decision = ""
            segments = []
            selected = None
            deezer_preview_url: str | None = None

            if strategy == "hybrid_deezer_youtube_representative":
                with Session(engine) as session:
                    deezer_ok, deezer_conf = self._availability.deezer_for_analysis(
                        session, item.track_id
                    )
                    preview_row = self._previews.get_for_track_provider(
                        session, track_id=item.track_id, provider="deezer"
                    )
                    if preview_row and preview_row.preview_url:
                        deezer_preview_url = ensure_fresh_deezer_preview_url(
                            session,
                            track_id=item.track_id,
                            preview_url=preview_row.preview_url,
                            provider_track_id=preview_row.provider_track_id,
                            previews=self._previews,
                        )
                        session.commit()

                if self._is_test:
                    candidates = self._provider.resolve(ctx)  # type: ignore[union-attr]
                    selected = next((c for c in candidates if c.selected), None)
                    yt_available = selected is not None
                    yt_conf = selected.confidence if selected else 0.0
                else:
                    candidates = self._provider.resolve(ctx)  # type: ignore[union-attr]
                    selected = next((c for c in candidates if c.selected), None)
                    yt_conf = selected.confidence if selected else 0.0
                    yt_available = (
                        selected is not None and yt_conf >= settings.youtube_min_confidence
                    )

                segments, analysis_decision = plan_hybrid_for_track(
                    ctx,
                    analysis_mode=analysis_mode,
                    segment_duration_seconds=seg_dur,
                    deezer_preview_available=deezer_ok,
                    youtube_available=yt_available,
                    youtube_confidence=yt_conf if selected else None,
                    deezer_match_confidence=deezer_conf,
                )
            else:
                if self._is_test:
                    candidates = self._provider.resolve(ctx)  # type: ignore[union-attr]
                else:
                    candidates = self._provider.resolve(ctx)  # type: ignore[union-attr]
                selected = next((c for c in candidates if c.selected), None)
                if selected is None:
                    raise RuntimeError("No suitable audio source found")
                segments = plan_segments_for_track(
                    ctx,
                    strategy,
                    analysis_mode=analysis_mode,
                    segment_duration_seconds=seg_dur,
                )
                analysis_decision = strategy

            if analysis_decision == ANALYSIS_UNAVAILABLE or not segments:
                with Session(engine) as session:
                    row = self._downloads.get(session, download_id)
                    if row:
                        row.status = "failed"
                        row.last_error = "Local analysis unavailable"
                        row.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
                        row.result_json = json.dumps(
                            redact_dict({"analysis_decision": ANALYSIS_UNAVAILABLE})
                        )
                    session.commit()
                self._items.mark_skipped(
                    item.id,
                    reason=LOCAL_ANALYSIS_UNAVAILABLE,
                )
                return

            created = 0
            for seg in segments:
                if seg.source == "deezer_preview":
                    if not deezer_preview_url:
                        raise RuntimeError("Deezer preview URL missing for segment download")
                    rel, fhash = download_deezer_preview_segment(
                        ctx,
                        job_id=item.job_id,
                        segment=seg,
                        preview_url=deezer_preview_url,
                    )
                    source = "deezer_preview"
                    url_hash = source_url_hash(deezer_preview_url)
                elif self._is_test:
                    rel, fhash = self._provider.materialize_segment(  # type: ignore[union-attr]
                        ctx, job_id=item.job_id, segment=seg
                    )
                    source = selected.source if selected else "test"
                    url_hash = source_url_hash(selected.url) if selected else None
                else:
                    if selected is None:
                        raise RuntimeError("No YouTube source for segment download")
                    rel, fhash = self._provider.download_segment(  # type: ignore[union-attr]
                        ctx,
                        job_id=item.job_id,
                        segment=seg,
                        source_url=selected.url,
                    )
                    source = selected.source
                    url_hash = source_url_hash(selected.url)

                with Session(engine) as session:
                    self._segments.insert(
                        session,
                        TrackSegment(
                            track_id=item.track_id,
                            download_job_id=download_id,
                            start_seconds=seg.start_seconds,
                            end_seconds=seg.end_seconds,
                            duration_seconds=seg.duration_seconds,
                            segment_type=seg.segment_type,
                            source=source,
                            source_quality=seg.source_quality,
                            source_url_hash=url_hash,
                            temporary_path=rel,
                            file_hash=fhash,
                            confidence=seg.match_confidence,
                            created_at=now,
                        ),
                    )
                    session.commit()
                    created += 1

            result = {
                "segments_created": created,
                "segments_planned": len(segments),
                "analysis_decision": analysis_decision,
                "analysis_mode": analysis_mode,
            }
            if selected:
                result["source"] = selected.source
            with Session(engine) as session:
                row = self._downloads.get(session, download_id)
                if row:
                    row.status = "success"
                    row.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
                    payload: dict = {"analysis_decision": analysis_decision, **result}
                    if not self._is_test and strategy != "abc_default":
                        payload["candidates_redacted"] = True
                    elif hasattr(self._provider, "resolution_json"):
                        payload = json.loads(
                            self._provider.resolution_json(candidates)  # type: ignore[union-attr]
                        )
                        payload["analysis_decision"] = analysis_decision
                    row.result_json = json.dumps(redact_dict(payload))
                    row.source_url = None
                session.commit()
            self._items.mark_success(item.id, result_json=result)
        except Exception as e:
            with Session(engine) as session:
                row = self._downloads.get(session, download_id)
                if row:
                    row.status = "failed"
                    row.last_error = str(e)[:2000]
                    row.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
                session.commit()
            retryable = "timeout" in str(e).lower() or "rate" in str(e).lower()
            self._items.mark_failed(
                item.id,
                error_code="AUDIO_DOWNLOAD_FAILED",
                error_message=str(e)[:500],
                retryable=retryable,
            )

    def _process_pipeline_segment_download(self, item: ReservedJobItem) -> None:
        """Download one pipeline stage segment and hand off to analyzers (streaming mode)."""
        assert item.track_id is not None
        inp = item.input_json
        planned_raw = inp.get("planned_segment")
        if not isinstance(planned_raw, dict):
            self._items.mark_failed(
                item.id,
                error_code="INVALID_ITEM",
                error_message="Missing planned_segment in pipeline download item",
            )
            return

        planned = planned_segment_from_dict(planned_raw)
        engine = get_engine()
        try:
            with Session(engine) as session:
                ctx = load_track_context(session, item.track_id)
            selected = None
            if self._is_test:
                candidates = self._provider.resolve(ctx)  # type: ignore[union-attr]
                selected = next((c for c in candidates if c.selected), None)

            with Session(engine) as session:
                download_id = create_audio_download_job_row(
                    session,
                    job_id=item.job_id,
                    track_id=item.track_id,
                    provider_name=inp.get("provider", "ytdlp"),
                    attempt_count=item.attempt_count,
                )
                segment_id, source = download_planned_segment(
                    session,
                    ctx=ctx,
                    job_id=item.job_id,
                    track_id=item.track_id,
                    planned=planned,
                    provider=self._provider,
                    is_test=self._is_test,
                    selected_source=selected,
                    deezer_preview_url=None,
                    download_job_id=download_id,
                )
                segment_index = inp.get("segment_index")
                self._handoff.on_segment_ready(
                    session,
                    job_id=item.job_id,
                    track_id=item.track_id,
                    segment_id=segment_id,
                    download_item_id=item.id,
                    segment_index=int(segment_index) if segment_index is not None else None,
                )
                row = self._downloads.get(session, download_id)
                if row:
                    row.status = "success"
                    row.finished_at = datetime.now(tz=UTC).replace(tzinfo=None)
                    row.result_json = json.dumps(
                        redact_dict(
                            {
                                "segment_id": segment_id,
                                "source": source,
                                "segment_index": segment_index,
                            }
                        )
                    )
                session.commit()

            self._handoff.complete_segment_handoff(item.job_id)
            self._items.mark_success(
                item.id,
                result_json={
                    "segment_id": segment_id,
                    "source": source,
                    "handoff": "segment_ready",
                },
            )
        except Exception as e:
            retryable = "timeout" in str(e).lower() or "rate" in str(e).lower()
            self._items.mark_failed(
                item.id,
                error_code="AUDIO_DOWNLOAD_FAILED",
                error_message=str(e)[:500],
                retryable=retryable,
            )
