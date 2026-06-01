from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_jobs import Job
from app.features.reccobeats_batch import (
    TrackEnrichContext,
    batch_entry_to_fetch_result,
    build_batch_raw_payload_json,
    chunk_contexts,
    load_enrich_contexts,
    request_id_for,
)
from app.features.reccobeats_mapper import map_reccobeats_result
from app.features.track_selection import FeatureTrackSelectionService
from app.features.upsert import FeatureUpsertService
from app.jobs.errors import JobCancelledError
from app.jobs.service import JobService
from app.library.job_progress import report_job_progress
from app.observability.debug_session_log import debug_session_log
from app.observability.errors import ApiError
from app.reccobeats.client import ReccoBeatsClient
from app.reccobeats.errors import ReccoBeatsError
from app.reccobeats.schemas import ReccoBeatsFetchResult
from app.settings.config import settings

JOB_TYPE_RECCOBEATS_ENRICH = "reccobeats_enrichment"


class ReccoBeatsEnrichmentService:
    def __init__(
        self,
        *,
        jobs: JobService | None = None,
        client: ReccoBeatsClient | None = None,
        upsert: FeatureUpsertService | None = None,
        selection: FeatureTrackSelectionService | None = None,
        sleeper: callable | None = None,
    ) -> None:
        self._jobs = jobs or JobService()
        self._client = client or ReccoBeatsClient()
        self._upsert = upsert or FeatureUpsertService()
        self._selection = selection or FeatureTrackSelectionService()
        self._sleep = sleeper or time.sleep

    def assert_no_running_job(self) -> None:
        reconciled = self._jobs.reconcile_orphaned_jobs(job_type=JOB_TYPE_RECCOBEATS_ENRICH)
        engine = get_engine()
        with Session(engine) as session:
            row = session.execute(
                select(Job.id, Job.status, Job.started_at, Job.progress_current).where(
                    Job.job_type == JOB_TYPE_RECCOBEATS_ENRICH,
                    Job.status.in_(("queued", "running")),
                )
            ).first()
            # #region agent log
            debug_session_log(
                location="features/enrichment.py:assert_no_running_job",
                message="running job gate check",
                data={
                    "reconciled": reconciled,
                    "blocking": (
                        {
                            "job_id": row[0],
                            "status": row[1],
                            "started_at": str(row[2]) if row else None,
                            "progress_current": row[3] if row else None,
                        }
                        if row
                        else None
                    ),
                    "active_in_memory": self._jobs.is_active(row[0]) if row else False,
                },
                hypothesis_id="H1-H3",
            )
            # #endregion
            if row is not None:
                raise ApiError(
                    code="JOB_ALREADY_RUNNING",
                    message="A ReccoBeats enrichment job is already running",
                    status_code=409,
                    details={"job_id": row[0]},
                )

    def start_enrichment_job(
        self,
        *,
        track_ids: list[int] | None = None,
        filter_dict: dict[str, Any] | None = None,
        batch_size: int = 50,
        only_missing: bool = True,
        retry_failed: bool = False,
        force_refresh: bool = False,
        limit: int | None = None,
    ) -> str:
        self.assert_no_running_job()
        job_id = self._jobs.create(JOB_TYPE_RECCOBEATS_ENRICH)

        def _run() -> dict[str, Any]:
            return self.run_enrichment(
                job_id,
                track_ids=track_ids,
                filter_dict=filter_dict,
                batch_size=batch_size,
                only_missing=only_missing,
                retry_failed=retry_failed,
                force_refresh=force_refresh,
                limit=limit,
            )

        self._jobs.start_background(job_id, _run)
        return job_id

    def run_enrichment(
        self,
        job_id: str,
        *,
        track_ids: list[int] | None = None,
        filter_dict: dict[str, Any] | None = None,
        batch_size: int = 50,
        only_missing: bool = True,
        retry_failed: bool = False,
        force_refresh: bool = False,
        limit: int | None = None,
    ) -> dict[str, Any]:
        engine = get_engine()
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        self._jobs.update(job_id, status="running", started_at=now, current_step="resolving_tracks")

        stats: dict[str, Any] = {
            "succeeded": 0,
            "failed": 0,
            "not_found": 0,
            "partial": 0,
            "skipped": 0,
            "errors_sample": [],
            "http_batches": 0,
        }

        with Session(engine) as session:
            ids = self._selection.resolve_track_ids(
                session,
                track_ids=track_ids,
                filter_dict=filter_dict,
                only_missing=only_missing,
                retry_failed=retry_failed,
                force_refresh=force_refresh,
                limit=limit,
            )
            session.commit()

        total = len(ids)
        self._jobs.update(
            job_id,
            progress_total=total,
            progress_current=0,
            current_step="loading_track_contexts",
        )

        with Session(engine) as session:
            contexts = load_enrich_contexts(session, ids)
            session.commit()

        work: list[tuple[TrackEnrichContext, str]] = []
        skipped_count = 0
        with Session(engine) as session:
            for ctx in contexts:
                req_id = request_id_for(ctx, force_refresh=force_refresh)
                if req_id is None:
                    self._apply_skipped_no_id(
                        session,
                        ctx=ctx,
                        force_refresh=force_refresh,
                        retry_failed=retry_failed,
                        stats=stats,
                    )
                    skipped_count += 1
                else:
                    work.append((ctx, req_id))
            session.commit()

        delay_sec = settings.reccobeats_batch_delay_ms / 1000.0
        http_chunk_size = max(1, min(40, int(settings.reccobeats_http_batch_size)))
        processed = skipped_count

        self._jobs.update(job_id, current_step="enriching_tracks")
        # #region agent log
        debug_session_log(
            location="features/enrichment.py:run_enrichment",
            message="enrichment http batch config",
            data={
                "job_id": job_id,
                "http_chunk_size": http_chunk_size,
                "work_count": len(work),
                "pause_every_n_tracks": batch_size,
            },
            hypothesis_id="H-batch",
        )
        # #endregion

        for chunk in chunk_contexts(work, http_chunk_size):
            if self._jobs.is_cancel_requested(job_id):
                self._finish_cancelled(job_id, stats, processed=processed, total=total)
                raise JobCancelledError()

            request_ids = [req_id for _, req_id in chunk]
            # #region agent log
            debug_session_log(
                location="features/enrichment.py:batch_chunk",
                message="processing http chunk",
                data={"job_id": job_id, "chunk_size": len(request_ids)},
                hypothesis_id="H-batch",
            )
            # #endregion
            try:
                batch_result = self._client.get_audio_features_batch(request_ids)
            except ReccoBeatsError as exc:
                for ctx, _req_id in chunk:
                    processed += 1
                    with Session(engine) as session:
                        self._apply_error(
                            session,
                            ctx=ctx,
                            exc=exc,
                            force_refresh=force_refresh,
                            retry_failed=retry_failed,
                            stats=stats,
                        )
                        report_job_progress(
                            session,
                            self._jobs,
                            job_id,
                            idx=processed,
                            progress_current=processed,
                            current_step="enriching_tracks",
                        )
                if processed % batch_size == 0:
                    self._sleep(delay_sec)
                continue

            stats["http_batches"] = int(stats["http_batches"]) + 1
            entries_by_id = {e.request_id: e for e in batch_result.entries}

            with Session(engine) as session:
                for ctx, req_id in chunk:
                    if self._jobs.is_cancel_requested(job_id):
                        session.commit()
                        self._finish_cancelled(job_id, stats, processed=processed, total=total)
                        raise JobCancelledError()
                    entry = entries_by_id.get(req_id)
                    fetch_result = batch_entry_to_fetch_result(
                        entry, ctx, batch_result=batch_result
                    )
                    payload_json = None
                    if entry is not None and entry.raw:
                        payload_json = build_batch_raw_payload_json(
                            fetch_result,
                            batch_result=batch_result,
                            entry=entry,
                        )

                    self._apply_fetch_result(
                        session,
                        ctx=ctx,
                        fetch_result=fetch_result,
                        force_refresh=force_refresh,
                        retry_failed=retry_failed,
                        stats=stats,
                        payload_json=payload_json,
                    )
                    processed += 1
                    report_job_progress(
                        session,
                        self._jobs,
                        job_id,
                        idx=processed,
                        progress_current=processed,
                        current_step="enriching_tracks",
                    )

                session.commit()

            self._jobs.update(
                job_id,
                progress_current=processed,
                current_step="enriching_tracks",
            )

            if processed % batch_size == 0:
                self._sleep(delay_sec)

        finished = datetime.now(tz=UTC).replace(tzinfo=None)
        self._jobs.update(
            job_id,
            status="succeeded",
            progress_current=total,
            current_step="complete",
            finished_at=finished,
            result_json=stats,
        )
        return stats

    def _finish_cancelled(
        self,
        job_id: str,
        stats: dict[str, Any],
        *,
        processed: int,
        total: int,
    ) -> None:
        finished = datetime.now(tz=UTC).replace(tzinfo=None)
        self._jobs.clear_cancel_request(job_id)
        self._jobs.update(
            job_id,
            status="cancelled",
            progress_current=processed,
            progress_total=total,
            current_step="cancelled",
            finished_at=finished,
            result_json=stats,
            last_error="Cancelled by user",
        )

    def _apply_skipped_no_id(
        self,
        session: Session,
        *,
        ctx: TrackEnrichContext,
        force_refresh: bool,
        retry_failed: bool,
        stats: dict[str, Any],
    ) -> None:
        from app.features.reccobeats_mapper import NormalizedFeatureRow

        fetch_result = ReccoBeatsFetchResult(track=None, features=None)
        self._upsert.upsert_reccobeats(
            session,
            track_id=ctx.track_id,
            fetch_result=fetch_result,
            normalized=NormalizedFeatureRow(
                status="skipped",
                error_code="NO_SPOTIFY_ID",
                error_message="Track has no Spotify ID, ISRC, or cached ReccoBeats ID",
            ),
            force_refresh=force_refresh,
            replace_failed=retry_failed,
        )
        stats["skipped"] += 1

    def _apply_error(
        self,
        session: Session,
        *,
        ctx: TrackEnrichContext,
        exc: ReccoBeatsError,
        force_refresh: bool,
        retry_failed: bool,
        stats: dict[str, Any],
    ) -> None:
        from app.features.reccobeats_mapper import NormalizedFeatureRow

        fetch_result = ReccoBeatsFetchResult(track=None, features=None)
        self._upsert.upsert_reccobeats(
            session,
            track_id=ctx.track_id,
            fetch_result=fetch_result,
            normalized=NormalizedFeatureRow(
                status="failed",
                error_code=exc.code,
                error_message=str(exc),
            ),
            force_refresh=force_refresh,
            replace_failed=retry_failed,
        )
        stats["failed"] += 1
        if len(stats["errors_sample"]) < 10:
            stats["errors_sample"].append({"track_id": ctx.track_id, "error": str(exc)})

    def _apply_fetch_result(
        self,
        session: Session,
        *,
        ctx: TrackEnrichContext,
        fetch_result: ReccoBeatsFetchResult,
        force_refresh: bool,
        retry_failed: bool,
        stats: dict[str, Any],
        payload_json: str | None = None,
    ) -> None:
        normalized = map_reccobeats_result(fetch_result, local_isrc=ctx.isrc)
        _row_id, applied = self._upsert.upsert_reccobeats(
            session,
            track_id=ctx.track_id,
            fetch_result=fetch_result,
            normalized=normalized,
            force_refresh=force_refresh,
            replace_failed=retry_failed,
            payload_json=payload_json,
        )

        if not applied:
            return

        if normalized.status == "success":
            stats["succeeded"] += 1
        elif normalized.status == "partial":
            stats["partial"] += 1
        elif normalized.status == "not_found":
            stats["not_found"] += 1
        elif normalized.status == "skipped":
            stats["skipped"] += 1
        else:
            stats["failed"] += 1
