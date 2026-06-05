from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.essentia_aggregate import aggregate_segment_features
from app.audio.essentia_parser import parsed_segment_from_features_json
from app.audio.pipeline.constants import (
    STAGE_ESSENTIA_LOWLEVEL,
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
    STAGE_FEATURE_AGGREGATION,
    TERMINAL_FOR_DEPENDENCY,
)

_TF_SEGMENT_STAGES = (
    STAGE_ESSENTIA_TENSORFLOW,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS,
)
_TF_STAGE_PRIORITY = {
    STAGE_ESSENTIA_TENSORFLOW: 3,
    STAGE_ESSENTIA_TENSORFLOW_EMBEDDINGS: 2,
    STAGE_ESSENTIA_TENSORFLOW_CLASSIFIERS: 1,
}
from app.audio.tensorflow.genre_runner import GENRE_MODEL_KEY
from app.audio.pipeline.orchestrator import _prerequisites_met
from app.database.engine import get_engine
from app.database.models_job_items import JobItem
from app.database.repositories.track_advanced_features import (
    AdvancedFeatureUpsertRow,
    TrackAdvancedFeaturesRepository,
)
from app.database.repositories.track_embeddings import (
    TrackEmbeddingUpsertRow,
    TrackEmbeddingsRepository,
)
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.features.embeddings.genre_discogs import (
    aggregate_genre_top_k,
    genre_features_from_top_k,
    parse_genre_segment_output,
)
from app.features.embeddings.constants import GENRE_FEATURE_NAMES
from app.features.embeddings.vector_aggregate import aggregate_vectors
from app.features.advanced.aggregate import aggregate_track_classifier_features
from app.features.advanced.energy_proxy import compute_energy_proxy
from app.features.advanced.mappers import feature_names_for_model_key
from app.features.upsert import FeatureUpsertService
from app.jobs.items.service import JobItemService
from app.models_registry.profile_scope import model_key_in_default_profile
from app.settings.config import settings


class PipelineFeatureAggregationService:
    def __init__(
        self,
        *,
        items: JobItemService | None = None,
        segments: TrackSegmentsRepository | None = None,
        upsert: FeatureUpsertService | None = None,
        advanced_repo: TrackAdvancedFeaturesRepository | None = None,
        embeddings_repo: TrackEmbeddingsRepository | None = None,
    ) -> None:
        self._items = items or JobItemService()
        self._segments = segments or TrackSegmentsRepository()
        self._upsert = upsert or FeatureUpsertService()
        self._advanced = advanced_repo or TrackAdvancedFeaturesRepository()
        self._embeddings = embeddings_repo or TrackEmbeddingsRepository()

    def try_run_pending_for_job(self, job_id: str) -> int:
        processed = 0
        engine = get_engine()
        with Session(engine) as session:
            pending = list(
                session.scalars(
                    select(JobItem).where(
                        JobItem.job_id == job_id,
                        JobItem.stage_name == STAGE_FEATURE_AGGREGATION,
                        JobItem.status == "pending",
                    )
                )
            )
        for item in pending:
            if self._run_aggregation_item(item.id):
                processed += 1
        return processed

    def _run_aggregation_item(self, item_id: str) -> bool:
        engine = get_engine()
        with Session(engine) as session:
            item = session.get(JobItem, item_id)
            if item is None or item.stage_name != STAGE_FEATURE_AGGREGATION:
                return False
            if item.status != "pending":
                return False
            if not _prerequisites_met(session, item):
                return False
            track_id = item.track_id
            job_id = item.job_id
            if track_id is None:
                return False

            ll_items = list(
                session.scalars(
                    select(JobItem).where(
                        JobItem.job_id == job_id,
                        JobItem.track_id == track_id,
                        JobItem.stage_name == STAGE_ESSENTIA_LOWLEVEL,
                        JobItem.status == "success",
                    )
                )
            )
            parsed_list = []
            for ll in ll_items:
                if ll.segment_id is None:
                    continue
                seg = self._segments.get(session, ll.segment_id)
                if seg is None or not seg.features_json:
                    continue
                try:
                    parsed = parsed_segment_from_features_json(seg.features_json)
                except (json.JSONDecodeError, ValueError):
                    continue
                parsed_list.append(parsed)

            aggregated = None
            if parsed_list:
                segments_planned = len(ll_items)
                aggregated = aggregate_segment_features(
                    parsed_list,
                    segments_planned=segments_planned,
                    segments_missing_reason="segment_analysis_incomplete"
                    if len(parsed_list) < segments_planned
                    else None,
                )
                self._upsert.upsert_essentia_lowlevel(
                    session,
                    track_id=track_id,
                    aggregated=aggregated,
                    force_refresh=False,
                )

            clf_segment_outputs, clf_models_missing = self._collect_classifier_outputs(
                session, job_id=job_id, track_id=track_id
            )
            emb_vectors, genre_segments, emb_models_missing, genre_error_codes = (
                self._collect_embedding_outputs(session, job_id=job_id, track_id=track_id)
            )

            advanced_rows = self._build_advanced_rows(
                track_id=track_id,
                segment_outputs=clf_segment_outputs,
                models_missing=clf_models_missing,
                aggregated=aggregated,
                genre_segments=genre_segments,
                emb_models_missing=emb_models_missing,
                genre_error_codes=genre_error_codes,
            )
            if advanced_rows:
                self._advanced.upsert_many(session, advanced_rows)

            embeddings_written = self._persist_track_embeddings(
                session,
                track_id=track_id,
                vectors_by_key=emb_vectors,
                emb_models_missing=emb_models_missing,
            )

            if aggregated is None and not advanced_rows and embeddings_written == 0:
                return False

            session.commit()
            segments_analyzed = len(parsed_list)
            result_bpm = aggregated.bpm if aggregated else None

        result_json: dict = {
            "segments_analyzed": segments_analyzed,
            "pipeline_version": settings.essentia_lowlevel_pipeline_version,
            "advanced_features_written": len(advanced_rows),
            "embeddings_written": embeddings_written,
            "genre_features_written": sum(
                1 for r in advanced_rows if r.feature_name in GENRE_FEATURE_NAMES
            ),
            "models_missing_count": len(clf_models_missing | emb_models_missing),
        }
        if result_bpm is not None:
            result_json["bpm"] = result_bpm

        self._items.mark_success(item_id, result_json=result_json)
        return True

    def _collect_classifier_outputs(
        self,
        session: Session,
        *,
        job_id: str,
        track_id: int,
    ) -> tuple[list[dict], set[str]]:
        segment_outputs: list[dict] = []
        models_missing: set[str] = set()
        for _segment_id, payload in self._collect_tensorflow_segment_outputs(
            session, job_id=job_id, track_id=track_id
        ):
            outputs = payload.get("classifier_outputs")
            if isinstance(outputs, dict):
                segment_outputs.append(outputs)
            missing = payload.get("models_missing")
            if isinstance(missing, list):
                models_missing.update(str(m) for m in missing)
        return segment_outputs, models_missing

    def _collect_embedding_outputs(
        self,
        session: Session,
        *,
        job_id: str,
        track_id: int,
    ) -> tuple[dict[str, list[list[float]]], list[list], set[str], list[str]]:
        vectors_by_key: dict[str, list[list[float]]] = {}
        genre_segments: list[list] = []
        genre_error_codes: list[str] = []
        models_missing: set[str] = set()

        for _segment_id, payload in self._collect_tensorflow_segment_outputs(
            session, job_id=job_id, track_id=track_id
        ):
            embedding_outputs = payload.get("embedding_outputs")
            if isinstance(embedding_outputs, dict):
                for model_key, out in embedding_outputs.items():
                    if not isinstance(out, dict):
                        continue
                    vector = out.get("vector")
                    if isinstance(vector, list):
                        vectors_by_key.setdefault(str(model_key), []).append(
                            [float(x) for x in vector]
                        )
            genre_outputs = payload.get("genre_outputs")
            if isinstance(genre_outputs, dict):
                genre_out = genre_outputs.get(GENRE_MODEL_KEY)
                if isinstance(genre_out, dict):
                    parsed = parse_genre_segment_output(genre_out)
                    if parsed:
                        genre_segments.append(parsed)
                    else:
                        err = genre_out.get("error_code")
                        if isinstance(err, str) and err:
                            genre_error_codes.append(err)
            missing = payload.get("models_missing")
            if isinstance(missing, list):
                models_missing.update(str(m) for m in missing)

        return vectors_by_key, genre_segments, models_missing, genre_error_codes

    def _collect_tensorflow_segment_outputs(
        self,
        session: Session,
        *,
        job_id: str,
        track_id: int,
    ) -> list[tuple[int | None, dict]]:
        tf_items = list(
            session.scalars(
                select(JobItem).where(
                    JobItem.job_id == job_id,
                    JobItem.track_id == track_id,
                    JobItem.stage_name.in_(_TF_SEGMENT_STAGES),
                    JobItem.status == "success",
                )
            )
        )
        best_by_segment: dict[int | None, tuple[int, dict]] = {}
        for item in tf_items:
            if not item.result_json:
                continue
            try:
                payload = json.loads(item.result_json)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            stage = item.stage_name or ""
            priority = _TF_STAGE_PRIORITY.get(stage, 0)
            segment_id = item.segment_id
            current = best_by_segment.get(segment_id)
            if current is None or priority > current[0]:
                best_by_segment[segment_id] = (priority, payload)
        return [(seg_id, payload) for seg_id, (_prio, payload) in best_by_segment.items()]

    def _persist_track_embeddings(
        self,
        session: Session,
        *,
        track_id: int,
        vectors_by_key: dict[str, list[list[float]]],
        emb_models_missing: set[str],
    ) -> int:
        pipeline_tf = settings.essentia_tensorflow_pipeline_version
        written = 0
        for model_key, vectors in vectors_by_key.items():
            if not vectors:
                continue
            dimension = len(vectors[0])
            agg = aggregate_vectors(vectors, expected_dimension=dimension)
            if agg is None:
                continue
            self._embeddings.upsert(
                session,
                TrackEmbeddingUpsertRow(
                    track_id=track_id,
                    source="essentia_tensorflow",
                    model_name=model_key,
                    dimension=agg.dimension,
                    vector_json=json.dumps(agg.vector),
                    pipeline_version=pipeline_tf,
                    aggregation_method="mean",
                    segments_used=agg.segments_used,
                    status=agg.status,
                    confidence=agg.confidence,
                ),
            )
            written += 1
        del emb_models_missing  # genre/effnet missing handled via advanced rows
        return written

    def _build_advanced_rows(
        self,
        *,
        track_id: int,
        segment_outputs: list[dict],
        models_missing: set[str],
        aggregated,
        genre_segments: list[list] | None = None,
        emb_models_missing: set[str] | None = None,
        genre_error_codes: list[str] | None = None,
    ) -> list[AdvancedFeatureUpsertRow]:
        pipeline_tf = settings.essentia_tensorflow_pipeline_version
        rows: list[AdvancedFeatureUpsertRow] = []

        if segment_outputs:
            for agg in aggregate_track_classifier_features(segment_outputs):
                rows.append(
                    AdvancedFeatureUpsertRow(
                        track_id=track_id,
                        feature_name=agg.feature_name,
                        value_float=agg.value,
                        confidence=agg.confidence,
                        source="essentia_tensorflow",
                        model_name=agg.model_key,
                        pipeline_version=pipeline_tf,
                        aggregation_method="median",
                        status=agg.status,
                    )
                )

        written_names = {r.feature_name for r in rows}
        for model_key in sorted(models_missing):
            if not model_key_in_default_profile(model_key):
                continue
            for feature_name in feature_names_for_model_key(model_key):
                if feature_name in written_names:
                    continue
                rows.append(
                    AdvancedFeatureUpsertRow(
                        track_id=track_id,
                        feature_name=feature_name,
                        value_float=None,
                        confidence=None,
                        source="essentia_tensorflow",
                        model_name=model_key,
                        pipeline_version=pipeline_tf,
                        status="model_missing",
                    )
                )
                written_names.add(feature_name)

        if genre_segments:
            genre_agg = aggregate_genre_top_k(genre_segments)
            if genre_agg is not None:
                for row in genre_features_from_top_k(
                    genre_agg,
                    model_name=GENRE_MODEL_KEY,
                    pipeline_version=pipeline_tf,
                ):
                    if row["feature_name"] in written_names:
                        continue
                    rows.append(
                        AdvancedFeatureUpsertRow(
                            track_id=track_id,
                            feature_name=row["feature_name"],
                            value_float=row.get("value_float"),
                            value_text=row.get("value_text"),
                            value_json=row.get("value_json"),
                            confidence=row.get("confidence"),
                            source=row["source"],
                            model_name=row.get("model_name"),
                            pipeline_version=row.get("pipeline_version"),
                            aggregation_method=row.get("aggregation_method"),
                            status=row.get("status", "success"),
                        )
                    )
                    written_names.add(row["feature_name"])

        emb_missing = emb_models_missing or set()
        genre_ok = bool(genre_segments)
        genre_err = (genre_error_codes or [None])[0] if genre_error_codes else None
        if not genre_ok and (GENRE_MODEL_KEY in emb_missing or genre_err):
            for feature_name in GENRE_FEATURE_NAMES:
                if feature_name in written_names:
                    continue
                rows.append(
                    AdvancedFeatureUpsertRow(
                        track_id=track_id,
                        feature_name=feature_name,
                        value_float=None,
                        value_text=genre_err if feature_name == "genre_discogs_519" else None,
                        confidence=None,
                        source="essentia_tensorflow",
                        model_name=GENRE_MODEL_KEY,
                        pipeline_version=pipeline_tf,
                        status="model_missing",
                    )
                )
                written_names.add(feature_name)

        if aggregated is not None:
            energy_val, energy_conf = compute_energy_proxy(aggregated)
            if energy_val is not None:
                rows.append(
                    AdvancedFeatureUpsertRow(
                        track_id=track_id,
                        feature_name="energy_proxy",
                        value_float=energy_val,
                        confidence=energy_conf,
                        source="derived",
                        model_name=None,
                        pipeline_version=settings.essentia_lowlevel_pipeline_version,
                        aggregation_method="weighted_mean",
                        status="success",
                    )
                )

        return rows
