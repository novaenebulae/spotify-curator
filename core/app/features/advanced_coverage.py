from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models_advanced_features import TrackAdvancedFeature
from app.database.models_library import Artist, Track, TrackArtist
from app.database.models_track_embeddings import TrackEmbedding
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.features.schemas import (
    AdvancedCoverageFeatureOut,
    AdvancedCoverageModelsSummaryOut,
    AdvancedCoverageResponse,
    AdvancedCoverageSummaryOut,
    AdvancedEmbeddingCoverageOut,
    AdvancedFailureOut,
)
from app.models_registry import ModelManager


_ADVANCED_FEATURE_NAMES: tuple[str, ...] = (
    "mood_aggressive_score",
    "mood_happy_score",
    "mood_party_score",
    "mood_relaxed_score",
    "mood_sad_score",
    "electronic_profile_score",
    "acoustic_profile_score",
    "approachability",
    "engagement",
    "danceability_tf",
    "arousal",
    "valence_tf",
    "voice_probability",
    "vocal_presence_score",
    "instrumental_focus_score",
    "genre_discogs_519",
    "genre_discogs_519_top_k",
    "energy_proxy",
)


class AdvancedFeatureCoverageService:
    def __init__(
        self,
        *,
        features_repo: AudioFeaturesRepository | None = None,
    ) -> None:
        self._features = features_repo or AudioFeaturesRepository()

    def get_coverage(
        self,
        session: Session,
        *,
        recent_failures_limit: int = 20,
    ) -> AdvancedCoverageResponse:
        track_count = self._features.count_tracks_total(session)
        features_out: list[AdvancedCoverageFeatureOut] = []

        for feature_name in _ADVANCED_FEATURE_NAMES:
            counts = self._status_counts_for_feature(session, feature_name)
            success = counts.get("success", 0) + counts.get("partial", 0)
            tracks_with = self._tracks_with_feature(session, feature_name, statuses=("success", "partial"))
            features_out.append(
                AdvancedCoverageFeatureOut(
                    feature_name=feature_name,
                    tracks_with_feature=tracks_with,
                    success_count=success,
                    model_missing_count=counts.get("model_missing", 0),
                    failed_count=counts.get("failed", 0),
                    missing_count=max(0, track_count - tracks_with),
                )
            )

        emb_row = session.execute(
            select(
                func.count(TrackEmbedding.id),
                func.count(func.distinct(TrackEmbedding.track_id)),
            ).where(TrackEmbedding.status.in_(("success", "partial")))
        ).one()
        emb_total, emb_tracks = int(emb_row[0] or 0), int(emb_row[1] or 0)

        models_summary = AdvancedCoverageModelsSummaryOut(
            real_inference_ready=False,
            default_profile="phase6-recommended",
            missing_model_keys=[],
        )
        try:
            status = ModelManager().get_status()
            summary = status.get("summary", {})
            models_summary.real_inference_ready = bool(summary.get("real_inference_ready"))
            models_summary.default_profile = str(summary.get("default_profile") or "phase6-recommended")
            available = {m["model_key"] for m in status.get("models", []) if m.get("status") == "available"}
            try:
                profile_keys = list(ModelManager().resolve_profile(models_summary.default_profile))
            except Exception:
                profile_keys = []
            models_summary.missing_model_keys = [k for k in profile_keys if k not in available]
        except Exception:
            pass

        failures = self._recent_failures(session, limit=recent_failures_limit)

        with_any = session.execute(
            select(func.count(func.distinct(TrackAdvancedFeature.track_id))).where(
                TrackAdvancedFeature.status.in_(("success", "partial"))
            )
        ).scalar_one()
        with_any = int(with_any or 0)

        return AdvancedCoverageResponse(
            summary=AdvancedCoverageSummaryOut(
                track_count=track_count,
                with_any_advanced_features=with_any,
                with_embeddings=emb_tracks,
            ),
            features=features_out,
            embeddings=AdvancedEmbeddingCoverageOut(
                rows_count=emb_total,
                tracks_with_embedding=emb_tracks,
            ),
            models_summary=models_summary,
            recent_failures=failures,
        )

    def _status_counts_for_feature(self, session: Session, feature_name: str) -> dict[str, int]:
        rows = session.execute(
            select(TrackAdvancedFeature.status, func.count(TrackAdvancedFeature.id))
            .where(TrackAdvancedFeature.feature_name == feature_name)
            .group_by(TrackAdvancedFeature.status)
        ).all()
        return {str(status): int(count) for status, count in rows}

    def _tracks_with_feature(
        self, session: Session, feature_name: str, *, statuses: tuple[str, ...]
    ) -> int:
        val = session.execute(
            select(func.count(func.distinct(TrackAdvancedFeature.track_id))).where(
                TrackAdvancedFeature.feature_name == feature_name,
                TrackAdvancedFeature.status.in_(statuses),
                TrackAdvancedFeature.value_float.is_not(None),
            )
        ).scalar_one()
        return int(val or 0)

    def _recent_failures(self, session: Session, *, limit: int) -> list[AdvancedFailureOut]:
        rows = list(
            session.execute(
                select(TrackAdvancedFeature, Track)
                .join(Track, Track.id == TrackAdvancedFeature.track_id)
                .where(TrackAdvancedFeature.status.in_(("failed", "model_missing")))
                .order_by(TrackAdvancedFeature.updated_at.desc().nullslast())
                .limit(limit)
            ).all()
        )
        out: list[AdvancedFailureOut] = []
        for feat, track in rows:
            out.append(
                AdvancedFailureOut(
                    track_id=track.id,
                    title=track.name,
                    artist_names=self._artist_names(session, track.id),
                    feature_name=feat.feature_name,
                    model_name=feat.model_name,
                    status=feat.status,
                    error_code=feat.status if feat.status == "model_missing" else "ADVANCED_FEATURE_FAILED",
                    error_message=None,
                )
            )
        return out

    def _artist_names(self, session: Session, track_id: int) -> list[str]:
        q = (
            select(Artist.name)
            .join(TrackArtist, TrackArtist.artist_id == Artist.id)
            .where(TrackArtist.track_id == track_id)
            .order_by(TrackArtist.position)
        )
        return list(session.scalars(q))
