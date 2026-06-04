from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.audio.paths import segment_absolute_path
from app.audio.pipeline.constants import (
    JOB_TYPE_AUDIO_ANALYSIS_PIPELINE,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
)
from app.audio.tensorflow.backend import EssentiaTensorflowBackend, TensorflowInferenceBackend
from app.audio.tensorflow.classifier_runner import ClassifierRunner
from app.audio.tensorflow.embeddings_runner import EmbeddingsRunner
from app.audio.tensorflow.errors import MODEL_INVALID, InferenceError
from app.audio.tensorflow.genre_runner import GenreRunner
from app.database.engine import get_engine
from app.database.models_job_items import JobItem
from app.database.models_jobs import Job
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.jobs.items.constants import WORKER_TYPE_ESSENTIA_TENSORFLOW
from app.jobs.items.service import ReservedJobItem
from app.models_registry import ModelRegistry
from app.models_registry.manager import ModelManager, ModelManagerError
from app.observability.redact import redact_dict
from app.settings.config import settings
from app.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


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
    ) -> None:
        super().__init__()
        self._registry = registry  # retained for backward compatibility; gating uses ModelManager
        self._mm = model_manager or ModelManager()
        self._backend = backend or EssentiaTensorflowBackend(model_manager=self._mm)
        self._segments = segments or TrackSegmentsRepository()
        self._classifier_runner = classifier_runner
        self._embeddings_runner = embeddings_runner
        self._genre_runner = genre_runner
        self._status_only = (
            status_only if status_only is not None else self._should_run_status_only()
        )
        self._models_summary: dict[str, object] = {}

    def _should_run_status_only(self) -> bool:
        if settings.essentia_tensorflow_status_only:
            return True
        return not bool(self._mm.get_status()["summary"].get("real_inference_ready"))

    def run_forever(self) -> None:
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
        super().run_forever()

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
            job is None
            or job_item is None
            or job.job_type != JOB_TYPE_AUDIO_ANALYSIS_PIPELINE
            or job_item.stage_name
            not in (STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS, STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS)
        ):
            self._items.mark_skipped(item.id, reason="Not a pipeline tensorflow stage item")
            return

        if self._status_only:
            self._items.mark_skipped(
                item.id,
                reason="tensorflow_status_only: required models missing or disabled",
            )
            return

        if item.segment_id is None:
            self._items.mark_failed(
                item.id,
                error_code="INVALID_ITEM",
                error_message="Pipeline tensorflow item missing segment_id",
            )
            return

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
                error_message="Segment audio file not found for tensorflow stage",
            )
            return

        self._heartbeat_running(
            current_job_id=item.job_id,
            current_item_id=item.id,
            metadata=redact_dict(
                {
                    "stage_name": job_item.stage_name,
                    "segment_id": item.segment_id,
                    "mode": "real" if self._backend is not None else "stub",
                }
            ),
        )

        result: dict = {
            "segment_id": item.segment_id,
            "stage_name": job_item.stage_name,
            "status_only": False,
        }

        try:
            if job_item.stage_name == STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS:
                runner = self._classifier_runner or ClassifierRunner(
                    model_manager=self._mm, backend=self._backend
                )
                clf = runner.run_for_segment(segment_id=item.segment_id, wav_path=str(wav))
                result["inference"] = clf.inference_mode
                result["classifier_outputs"] = clf.classifier_outputs
                result["models_missing"] = clf.models_missing
            else:
                emb = (
                    self._embeddings_runner
                    or EmbeddingsRunner(model_manager=self._mm, backend=self._backend)
                ).run_for_segment(segment_id=item.segment_id, wav_path=str(wav))
                result["inference"] = emb.inference_mode
                result["embedding_outputs"] = emb.embedding_outputs
                genre_missing: list[str] = []
                genre_outputs: dict = {}
                genre_mode = "none"
                try:
                    genre = (
                        self._genre_runner
                        or GenreRunner(model_manager=self._mm, backend=self._backend)
                    ).run_for_segment(segment_id=item.segment_id, wav_path=str(wav))
                    genre_outputs = genre.genre_outputs
                    genre_missing = list(genre.models_missing)
                    genre_mode = genre.inference_mode
                except (InferenceError, ModelManagerError) as genre_exc:
                    if _is_audio_too_short(genre_exc):
                        from app.audio.tensorflow.genre_runner import GENRE_MODEL_KEY

                        genre_missing = [GENRE_MODEL_KEY]
                    else:
                        raise
                result["genre_outputs"] = genre_outputs
                result["genre_inference"] = genre_mode
                result["models_missing"] = sorted(
                    set(emb.models_missing) | set(genre_missing)
                )
                if emb.inference_mode == "real" or genre_mode == "real":
                    result["inference"] = "real"
        except InferenceError as exc:
            self._items.mark_failed(
                item.id, error_code=exc.code, error_message=exc.message
            )
            return
        except ModelManagerError as exc:
            self._items.mark_failed(
                item.id, error_code=MODEL_INVALID, error_message=exc.message
            )
            return

        result["pipeline_version"] = self._pipeline_version(job_item, result["inference"])
        self._items.mark_success(item.id, result_json=result)
        missing = result.get("models_missing")
        if isinstance(missing, list) and missing:
            self._items.emit_model_missing(
                job_id=item.job_id,
                item_id=item.id,
                stage_name=job_item.stage_name,
                models_missing=[str(m) for m in missing],
            )

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
        self._heartbeat.register_or_update(
            worker_id=self._worker_id,
            worker_type=self.worker_type,
            status="running",
            current_job_id=current_job_id,
            current_item_id=current_item_id,
            metadata=redact_dict(meta),
        )


def _is_audio_too_short(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "too short" in msg or "signal is too short" in msg
