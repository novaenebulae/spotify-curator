from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_advanced_features import TrackAdvancedFeature
from app.database.models_library import Track
from app.database.models_features import AudioFeature
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.database.repositories.track_segments import TrackSegmentsRepository
from app.features.track_selection import FeatureTrackSelectionService
from app.library.search import TrackSearchService
from app.observability.errors import ApiError
from app.settings.config import settings


class AudioTrackSelectionService:
    def __init__(
        self,
        *,
        features_repo: AudioFeaturesRepository | None = None,
        sources_repo: FeatureSourcesRepository | None = None,
        segments_repo: TrackSegmentsRepository | None = None,
        feature_selection: FeatureTrackSelectionService | None = None,
        search_service: TrackSearchService | None = None,
    ) -> None:
        self._features = features_repo or AudioFeaturesRepository()
        self._sources = sources_repo or FeatureSourcesRepository()
        self._segments = segments_repo or TrackSegmentsRepository()
        self._feature_selection = feature_selection or FeatureTrackSelectionService()
        self._search = search_service or TrackSearchService()

    def resolve_for_download(
        self,
        session: Session,
        *,
        track_ids: list[int] | None,
        filter_dict: dict[str, Any] | None,
        only_missing: bool,
        retry_failed: bool,
        limit: int | None,
    ) -> list[int]:
        max_limit = min(limit or settings.audio_enrich_default_limit, settings.audio_enrich_max_limit)
        if track_ids is not None:
            ids = self._feature_selection._validate_track_ids(session, track_ids)  # noqa: SLF001
        elif filter_dict:
            ids = self._feature_selection._ids_from_filter(session, filter_dict, max_limit)  # noqa: SLF001
        else:
            ids = list(session.execute(select(Track.id).order_by(Track.id).limit(max_limit)).scalars())

        if only_missing and not retry_failed:
            # If a track already has a successful/partial Essentia low-level feature row, do not
            # download segments again (segments may have been cleaned after analysis).
            essentia = self._sources.get_by_name(session, "essentia_lowlevel")
            analyzed: set[int] = set()
            if essentia is not None:
                analyzed = set(
                    self._features.list_track_ids_with_status(
                        session,
                        feature_source_id=essentia.id,
                        statuses=("success", "partial"),
                        limit=max_limit,
                    )
                )
            ids = [i for i in ids if i not in analyzed and not self._has_active_segments(session, i)]
        elif retry_failed:
            source = self._sources.get_by_name(session, "essentia_lowlevel")
            if source:
                failed = set(
                    self._features.list_track_ids_failed_source(
                        session, feature_source_id=source.id, limit=max_limit
                    )
                )
                ids = [i for i in ids if i in failed or not self._has_active_segments(session, i)]
        return ids[:max_limit]

    def resolve_for_analysis(
        self,
        session: Session,
        *,
        track_ids: list[int] | None,
        filter_dict: dict[str, Any] | None,
        only_missing: bool,
        retry_failed: bool,
        force_refresh: bool,
        limit: int | None,
        require_existing_segments: bool,
    ) -> list[int]:
        max_limit = min(limit or settings.audio_enrich_default_limit, settings.audio_enrich_max_limit)
        if track_ids is not None:
            ids = self._feature_selection._validate_track_ids(session, track_ids)  # noqa: SLF001
        elif filter_dict:
            ids = self._feature_selection._ids_from_filter(session, filter_dict, max_limit)  # noqa: SLF001
        else:
            ids = list(session.execute(select(Track.id).order_by(Track.id).limit(max_limit)).scalars())

        essentia = self._sources.get_by_name(session, "essentia_lowlevel")
        reccobeats = self._sources.get_by_name(session, "reccobeats")
        if essentia is None:
            raise ApiError(
                code="INTERNAL_ERROR",
                message="essentia_lowlevel source not seeded",
                status_code=500,
            )

        by_track_source: dict[tuple[int, int], AudioFeature] = {}
        rows = list(
            session.execute(
                select(AudioFeature).where(
                    AudioFeature.is_active.is_(True),
                    AudioFeature.track_id.in_(ids),
                    AudioFeature.feature_source_id.in_(
                        [x for x in (essentia.id, reccobeats.id if reccobeats else None) if x is not None]
                    ),
                )
            ).scalars()
        )
        for r in rows:
            by_track_source[(r.track_id, r.feature_source_id)] = r

        def _needs_essentia_lowlevel(tid: int) -> bool:
            rb = (
                by_track_source.get((tid, reccobeats.id))
                if reccobeats is not None
                else None
            )
            # If ReccoBeats is missing/not usable, Essentia is our fallback.
            if rb is None:
                return True
            if rb.status in ("failed", "not_found", "pending", "missing"):
                return True
            # Otherwise, only run Essentia if it can fill missing fields.
            # (Low-level Essentia currently provides: bpm, loudness, key/mode, duration_ms.)
            return any(
                getattr(rb, field, None) is None
                for field in ("bpm", "loudness", "key", "mode", "duration_ms")
            )

        out: list[int] = []
        for tid in ids:
            if require_existing_segments and not self._has_active_segments(session, tid):
                continue
            if force_refresh:
                out.append(tid)
                continue
            if retry_failed:
                row = by_track_source.get((tid, essentia.id))
                if row and row.status == "failed":
                    out.append(tid)
                    continue
            if only_missing:
                row = by_track_source.get((tid, essentia.id))
                if row and row.status in ("success", "partial") and not force_refresh:
                    continue
                if not _needs_essentia_lowlevel(tid):
                    continue
            else:
                out.append(tid)
                continue
            out.append(tid)
        return out[:max_limit]

    def resolve_for_advanced_pipeline(
        self,
        session: Session,
        *,
        track_ids: list[int] | None,
        filter_dict: dict[str, Any] | None,
        only_missing: bool,
        retry_failed: bool,
        force_refresh: bool,
        limit: int | None,
        include_lowlevel: bool,
        include_tensorflow: bool,
        model_profile: str,
    ) -> list[int]:
        """Select tracks for the advanced analysis pipeline.

        With ``only_missing=True``, include a track when at least one requested stage
        (low-level and/or TensorFlow per ``include_*`` flags) is incomplete.
        ``model_profile`` is reserved for future profile-scoped TF completeness checks.
        """
        _ = model_profile
        max_limit = min(
            limit if limit is not None else settings.audio_enrich_max_limit,
            settings.audio_enrich_max_limit,
        )
        scan_limit = max_limit
        if (
            track_ids is None
            and only_missing
            and not force_refresh
            and not retry_failed
        ):
            if filter_dict:
                # Filtered batches (e.g. recent liked): widen scan so only_missing can fill quota.
                scan_limit = min(max(max_limit * 50, 500), settings.audio_enrich_max_limit)
            else:
                # Full-library only_missing: scan every track up to server max.
                scan_limit = settings.audio_enrich_max_limit
        if track_ids is not None:
            ids = self._feature_selection._validate_track_ids(session, track_ids)  # noqa: SLF001
        elif filter_dict:
            ids = self._feature_selection._ids_from_filter(session, filter_dict, scan_limit)  # noqa: SLF001
        else:
            ids = list(
                session.execute(select(Track.id).order_by(Track.id).limit(scan_limit)).scalars()
            )

        if not ids:
            return []

        essentia = self._sources.get_by_name(session, "essentia_lowlevel")
        lowlevel_by_track: dict[int, str] = {}
        if essentia is not None:
            rows = session.execute(
                select(AudioFeature.track_id, AudioFeature.status).where(
                    AudioFeature.track_id.in_(ids),
                    AudioFeature.feature_source_id == essentia.id,
                    AudioFeature.is_active.is_(True),
                )
            ).all()
            lowlevel_by_track = {int(tid): str(st) for tid, st in rows}

        tf_satisfied: set[int] = set()
        tf_failed: set[int] = set()
        if include_tensorflow:
            tf_satisfied = {
                int(r[0])
                for r in session.execute(
                    select(TrackAdvancedFeature.track_id)
                    .where(
                        TrackAdvancedFeature.track_id.in_(ids),
                        TrackAdvancedFeature.status.in_(("success", "partial")),
                        TrackAdvancedFeature.value_float.is_not(None),
                    )
                    .distinct()
                ).all()
            }
            tf_failed = {
                int(r[0])
                for r in session.execute(
                    select(TrackAdvancedFeature.track_id)
                    .where(
                        TrackAdvancedFeature.track_id.in_(ids),
                        TrackAdvancedFeature.status.in_(("failed", "model_missing")),
                    )
                    .distinct()
                ).all()
            }

        def _lowlevel_satisfied(tid: int) -> bool:
            return lowlevel_by_track.get(tid) in ("success", "partial")

        def _tensorflow_satisfied(tid: int) -> bool:
            return tid in tf_satisfied

        def _pipeline_complete(tid: int) -> bool:
            ll_ok = not include_lowlevel or _lowlevel_satisfied(tid)
            tf_ok = not include_tensorflow or _tensorflow_satisfied(tid)
            return ll_ok and tf_ok

        out: list[int] = []
        for tid in ids:
            if force_refresh:
                out.append(tid)
                continue
            if retry_failed:
                ll_failed = lowlevel_by_track.get(tid) == "failed"
                if ll_failed or tid in tf_failed:
                    out.append(tid)
                continue
            if only_missing:
                if not _pipeline_complete(tid):
                    out.append(tid)
                continue
            out.append(tid)
        return out[:max_limit]

    def _has_active_segments(self, session: Session, track_id: int) -> bool:
        segs = self._segments.list_active_with_file(session, track_id)
        return len(segs) > 0
