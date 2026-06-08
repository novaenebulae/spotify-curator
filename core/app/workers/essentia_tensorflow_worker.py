from __future__ import annotations

import json
import logging
import signal
import threading
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audio.paths import segment_absolute_path
from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
)
from app.audio.tensorflow.backend import EssentiaTensorflowBackend, TensorflowInferenceBackend
from app.audio.tensorflow.device import configure_tensorflow_device, device_info_to_dict
from app.audio.tensorflow.warmup import warmup_tensorflow_predictors
from app.audio.tensorflow.classifier_runner import ClassifierRunner
from app.audio.tensorflow.embeddings_runner import EmbeddingsRunner
from app.audio.tensorflow.errors import MODEL_INVALID, InferenceError
from app.audio.tensorflow.genre_runner import GenreRunner
from app.audio.tensorflow.segment_runner import SegmentTensorflowRunner
from app.database.engine import get_engine
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.jobs.items.constants import WORKER_TYPE_ESSENTIA_TENSORFLOW
from app.jobs.items.service import ReservedJobItem
from app.models_registry import ModelRegistry
from app.models_registry.manager import ModelManager, ModelManagerError
from app.models_registry.profile_scope import model_profile_from_job_result
from app.observability.redact import redact_dict
from app.settings.config import settings
from app.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)

_TF_PIPELINE_STAGES = frozenset(
    {
        STAGE_ESSENTIA_TENSORFLOW,
        STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
        STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    }
)
_TF_RESERVE_STAGE_ORDER = (
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
)
_LEGACY_CLASSIFIER_SKIP_REASON = "fulfilled by embeddings merge"
_IDLE_LOG_EVERY_N_POLLS = 12


class EssentiaTensorflowWorker(BaseWorker):
    worker_type = WORKER_TYPE_ESSENTIA_TENSORFLOW

    def __init__(
        self,
        *,
        registry: ModelRegistry | None = None,
        model_manager: ModelManager | None = None,
        backend: TensorflowInferenceBackend | None = None,
        segments: TrackSegmentsRepository | None = None,
        status_only: bool | None = None,
        classifier_runner: ClassifierRunner | None = None,
        embeddings_runner: EmbeddingsRunner | None = None,
        genre_runner: GenreRunner | None = None,
        segment_runner: SegmentTensorflowRunner | None = None,
    ) -> None:
        super().__init__()
        self._registry = registry  # retained for backward compatibility; gating uses ModelManager
        self._mm = model_manager or ModelManager()
        self._backend = backend or EssentiaTensorflowBackend(model_manager=self._mm)
        self._segments = segments or TrackSegmentsRepository()
        self._classifier_runner = classifier_runner
        self._embeddings_runner = embeddings_runner
        self._genre_runner = genre_runner
        self._segment_runner = segment_runner
        self._status_only = (
            status_only if status_only is not None else self._should_run_status_only()
        )
        self._models_summary: dict[str, object] = {}
        self._boot_metrics: dict[str, object] = {}

    def _should_run_status_only(self) -> bool:
        if settings.essentia_tensorflow_status_only:
            return True
        return not bool(self._mm.get_status()["summary"].get("real_inference_ready"))

    def run_forever(self) -> None:
        device_info = configure_tensorflow_device()
        models_summary = self._mm.get_status()["summary"]
        self._boot_metrics = {
            **device_info_to_dict(device_info),
            "run_env": settings.run_env,
            "app_env": settings.app_env,
            "database_url": settings.database_url,
            "models_dir": settings.models_dir,
            "real_inference_ready": models_summary.get("real_inference_ready"),
            "essentia_model_profile": settings.effective_essentia_model_profile,
            "warmup_enabled": settings.essentia_tf_warmup,
            "worker_id": self._worker_id,
        }
        logger.info(
            "essentia-tensorflow-worker tensorflow runtime",
            extra=self._boot_metrics,
        )

        if settings.essentia_tf_warmup and not self._status_only:
            backend = (
                self._backend
                if isinstance(self._backend, EssentiaTensorflowBackend)
                else EssentiaTensorflowBackend(model_manager=self._mm)
            )
            try:
                warmup_result = warmup_tensorflow_predictors(
                    model_manager=self._mm,
                    backend=backend,
                    profile=settings.effective_essentia_model_profile,
                )
                self._boot_metrics.update(warmup_result)
                logger.info(
                    "essentia-tensorflow-worker warmup complete",
                    extra=warmup_result,
                )
            except InferenceError as exc:
                logger.error(
                    "essentia-tensorflow-worker warmup failed: %s",
                    exc.message,
                    extra={"error_code": exc.code, **self._boot_metrics},
                )
                raise SystemExit(1) from exc

        self._models_summary = self._mm.get_status()["summary"]
        if self._status_only:
            logger.info(
                "essentia-tensorflow-worker starting in status_only mode",
                extra={"models_summary": self._models_summary},
            )
        else:
            logger.info(
                "essentia-tensorflow-worker starting with required models available",
                extra={"models_summary": self._models_summary},
            )

        signal.signal(signal.SIGTERM, self._handle_stop)
        signal.signal(signal.SIGINT, self._handle_stop)
        self._heartbeat.register_or_update(
            worker_id=self._worker_id,
            worker_type=self.worker_type,
            status="starting",
        )
        logger.info("Worker %s starting", self._worker_id)
        # Batch size coalesces pipeline refresh only; reservation stays at 1 item so
        # --scale essentia-tensorflow-worker=K can distribute segments across replicas.
        refresh_batch_size = max(1, settings.essentia_tensorflow_batch_size)
        job_ids_to_refresh: set[str] = set()
        processed_since_refresh = 0
        idle_polls = 0
        try:
            while self._running:
                self._heartbeat.register_or_update(
                    worker_id=self._worker_id,
                    worker_type=self.worker_type,
                    status="idle",
                )
                self._items.release_stale_locks(worker_type=self.worker_type)
                item = self._items.reserve_next(
                    worker_id=self._worker_id,
                    worker_type=self.worker_type,
                )
                if item is None:
                    self._flush_pipeline_refresh(job_ids_to_refresh)
                    job_ids_to_refresh.clear()
                    processed_since_refresh = 0
                    idle_polls += 1
                    if idle_polls % _IDLE_LOG_EVERY_N_POLLS == 0:
                        self._log_idle_pipeline_counts()
                    time.sleep(settings.job_worker_heartbeat_interval_seconds)
                    continue

                idle_polls = 0

                if self._items.is_job_cancelled(item.job_id):
                    self._items.mark_skipped(item.id, reason="Parent job cancelled")
                    continue
                try:
                    refresh = self._process_pipeline_item_with_heartbeat(item)
                except Exception as e:  # noqa: BLE001
                    logger.exception("Item %s failed: %s", item.id, e)
                    self._items.mark_failed(
                        item.id,
                        error_code="WORKER_ERROR",
                        error_message=str(e)[:500],
                        retryable=True,
                    )
                    continue
                if refresh:
                    job_ids_to_refresh.add(item.job_id)
                    processed_since_refresh += 1
                    if processed_since_refresh >= refresh_batch_size:
                        self._flush_pipeline_refresh(job_ids_to_refresh)
                        job_ids_to_refresh.clear()
                        processed_since_refresh = 0
        finally:
            self._heartbeat.register_or_update(
                worker_id=self._worker_id,
                worker_type=self.worker_type,
                status="stopping",
            )
            logger.info("Worker %s stopped", self._worker_id)

    def _handle_stop(self, *_args: object) -> None:
        self._running = False

    def _log_idle_pipeline_counts(self) -> None:
        engine = get_engine()
        counts: dict[str, dict[str, int]] = {}
        with Session(engine) as session:
            rows = session.execute(
                select(JobItem.stage_name, JobItem.status, func.count())
                .where(
                    JobItem.stage_name.in_(tuple(_TF_PIPELINE_STAGES)),
                    JobItem.status.in_(
                        ("pending", "running", "failed", "rate_limited", "blocked")
                    ),
                )
                .group_by(JobItem.stage_name, JobItem.status)
            ).all()
        for stage_name, status, count in rows:
            if stage_name is None:
                continue
            counts.setdefault(stage_name, {})[status] = int(count)
        logger.info(
            "essentia-tensorflow-worker idle: no pipeline item reserved",
            extra={
                "worker_id": self._worker_id,
                "database_url": settings.database_url,
                "stage_counts": counts,
                "status_only": self._status_only,
            },
        )

    def _flush_pipeline_refresh(self, job_ids: set[str]) -> None:
        for job_id in job_ids:
            self._items.refresh_pipeline_for_job(job_id)

    def process_item(self, item: object) -> None:
        assert isinstance(item, ReservedJobItem)
        self._process_pipeline_item_with_heartbeat(item)

    def _process_pipeline_item_with_heartbeat(self, item: ReservedJobItem) -> bool:
        stop = threading.Event()
        heartbeat_meta: dict[str, object] | None = None
        if item.stage_name:
            heartbeat_meta = {"stage_name": item.stage_name}

        def _pulse() -> None:
            while not stop.wait(timeout=settings.job_worker_heartbeat_interval_seconds):
                self._heartbeat_running(
                    current_job_id=item.job_id,
                    current_item_id=item.id,
                    metadata=redact_dict(dict(heartbeat_meta or {})),
                )

        self._heartbeat_running(
            current_job_id=item.job_id,
            current_item_id=item.id,
            metadata=redact_dict(dict(heartbeat_meta or {})),
        )
        pulse_thread = threading.Thread(target=_pulse, daemon=True)
        pulse_thread.start()
        try:
            return self._process_item_for_batch(item)
        finally:
            stop.set()
            pulse_thread.join(timeout=1.0)

    def _process_item_for_batch(self, item: ReservedJobItem) -> bool:
        """Process one item. Returns True if pipeline refresh is needed for the job."""
        if item.track_id is None:
            self._items.mark_failed(
                item.id, error_code="INVALID_ITEM", error_message="Missing track_id"
            )
            return False

        engine = get_engine()
        with Session(engine) as session:
            job = session.get(Job, item.job_id)
            job_item = session.get(JobItem, item.id)

        if (
            job is None
            or job_item is None
            or job.job_type != JOB_TYPE_AUDIO_ANALYSIS_PIPELINE
            or job_item.stage_name not in _TF_PIPELINE_STAGES
        ):
            self._items.mark_skipped(item.id, reason="Not a pipeline tensorflow stage item")
            return False

        if self._status_only:
            self._items.mark_skipped(
                item.id,
                reason="tensorflow_status_only: required models missing or disabled",
            )
            return True

        if item.segment_id is None:
            self._items.mark_failed(
                item.id,
                error_code="INVALID_ITEM",
                error_message="Pipeline tensorflow item missing segment_id",
            )
            return False

        if job_item.stage_name == STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS:
            if self._legacy_classifiers_fulfilled(item, job_item):
                self._items.mark_skipped(item.id, reason=_LEGACY_CLASSIFIER_SKIP_REASON)
                return True

        with Session(engine) as session:
            seg = self._segments.get(session, item.segment_id)
        if seg is None or seg.deleted_at is not None:
            self._items.mark_skipped(item.id, reason="Segment not found or deleted")
            return False

        wav = segment_absolute_path(seg.temporary_path or "")
        if not wav.is_file():
            self._items.mark_failed(
                item.id,
                error_code="SEGMENT_FILE_MISSING",
                error_message="Segment audio file not found for tensorflow stage",
            )
            return False

        try:
            model_profile = model_profile_from_job_result(job.result_json)
            result = self._run_segment_inference(
                segment_id=item.segment_id,
                wav_path=str(wav),
                stage_name=job_item.stage_name,
                model_profile=model_profile,
            )
        except InferenceError as exc:
            self._items.mark_failed(
                item.id, error_code=exc.code, error_message=exc.message
            )
            return False
        except ModelManagerError as exc:
            self._items.mark_failed(
                item.id, error_code=MODEL_INVALID, error_message=exc.message
            )
            return False

        result["pipeline_version"] = self._pipeline_version(job_item, result["inference"])
        timing = result.get("timing_ms")
        if isinstance(timing, dict) and timing:
            logger.info(
                "essentia-tensorflow segment complete",
                extra={
                    "worker_id": self._worker_id,
                    "segment_id": item.segment_id,
                    "job_id": item.job_id,
                    **timing,
                },
            )
        self._items.mark_success(item.id, result_json=result, refresh_pipeline=False)
        missing = result.get("models_missing")
        if isinstance(missing, list) and missing:
            self._items.emit_model_missing(
                job_id=item.job_id,
                item_id=item.id,
                stage_name=job_item.stage_name,
                models_missing=[str(m) for m in missing],
            )
        return True

    def _run_segment_inference(
        self,
        *,
        segment_id: int,
        wav_path: str,
        stage_name: str,
        model_profile: str,
    ) -> dict:
        runner = self._segment_runner or SegmentTensorflowRunner(
            model_manager=self._mm,
            backend=self._backend,
            embeddings_runner=self._embeddings_runner,
            genre_runner=self._genre_runner,
            classifier_runner=self._classifier_runner,
        )
        seg_result = runner.run_for_segment(
            segment_id=segment_id, wav_path=wav_path, model_profile=model_profile
        )
        return runner.to_result_json(seg_result, stage_name=stage_name)

    def _legacy_classifiers_fulfilled(
        self, item: ReservedJobItem, job_item: JobItem
    ) -> bool:
        if item.segment_id is None or job_item.depends_on_item_id is None:
            return False
        engine = get_engine()
        with Session(engine) as session:
            dep = session.get(JobItem, job_item.depends_on_item_id)
            if dep is None or dep.stage_name != STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS:
                return False
            if dep.status != "success" or not dep.result_json:
                return False
            try:
                payload = json.loads(dep.result_json)
            except json.JSONDecodeError:
                return False
            outputs = payload.get("classifier_outputs")
            return isinstance(outputs, dict) and bool(outputs)

    @staticmethod
    def _pipeline_version(job_item: JobItem, inference_mode: str) -> str:
        if job_item.pipeline_version:
            return job_item.pipeline_version
        if inference_mode == "real":
            return settings.essentia_tf_pipeline_version
        return settings.essentia_tensorflow_pipeline_version

    def _heartbeat_running(
        self,
        *,
        current_job_id: str | None = None,
        current_item_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        meta = dict(metadata or {})
        meta.setdefault("status_only", self._status_only)
        meta.setdefault("models_summary", self._models_summary)
        if self._boot_metrics:
            meta.setdefault("boot_metrics", self._boot_metrics)
        self._heartbeat.register_or_update(
            worker_id=self._worker_id,
            worker_type=self.worker_type,
            status="running",
            current_job_id=current_job_id,
            current_item_id=current_item_id,
            metadata=redact_dict(meta),
        )
