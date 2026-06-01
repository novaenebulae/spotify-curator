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
from app.jobs.items.constants import WORKER_TYPE_AUDIO_DOWNLOADER
from app.jobs.items.service import ReservedJobItem
from app.observability.redact import redact_dict
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

    def process_item(self, item: object) -> None:
        assert isinstance(item, ReservedJobItem)
        if item.track_id is None:
            self._items.mark_failed(
                item.id, error_code="INVALID_ITEM", error_message="Missing track_id"
            )
            return
        engine = get_engine()
        with Session(engine) as session:
            ctx = load_track_context(session, item.track_id)
        inp = item.input_json
        strategy = inp.get("strategy", settings.audio_segment_strategy)
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
                        deezer_preview_url = preview_row.preview_url

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
                    ctx, strategy, segment_duration_seconds=seg_dur
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
                "analysis_decision": analysis_decision,
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
