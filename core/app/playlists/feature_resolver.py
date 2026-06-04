from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_features import AudioFeature, FeatureSource
from app.database.models_library import (
    Album,
    Artist,
    ExternalId,
    LikedTrack,
    SpotifyTrack,
    Track,
    TrackArtist,
)
from app.database.models_playlists import Playlist, PlaylistTrack
from app.database.models_previews import TrackPreview
from app.database.models_advanced_features import TrackAdvancedFeature
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.database.repositories.track_advanced_features import TrackAdvancedFeaturesRepository
from app.database.repositories.track_embeddings import TrackEmbeddingsRepository
from app.database.models_track_embeddings import TrackEmbedding
from app.features.embeddings.constants import TIMBRE_EMBEDDING_DIM
from app.features.confidence import FEATURE_FIELD_NAMES, field_confidence
from app.playlists.feature_registry import FeatureRegistry, get_feature_registry
from app.playlists.types import FeatureValue, TrackFeatureView

_LOW_CONFIDENCE_THRESHOLD = 0.5

# Per-field preferred source when multiple active rows exist (phase 5).
_FIELD_SOURCE_PRIORITY: dict[str, tuple[str, ...]] = {
    "bpm": ("essentia_lowlevel", "reccobeats"),
    "loudness": ("essentia_lowlevel", "reccobeats"),
    "key": ("essentia_lowlevel", "reccobeats"),
    "mode": ("essentia_lowlevel", "reccobeats"),
    "energy": ("reccobeats", "essentia_lowlevel"),
    "valence": ("reccobeats",),
    "danceability": ("reccobeats",),
    "acousticness": ("reccobeats",),
    "instrumentalness": ("reccobeats",),
    "speechiness": ("reccobeats",),
    "liveness": ("reccobeats",),
    "time_signature": ("reccobeats",),
    "duration_ms": ("reccobeats",),
    "feature_confidence": ("reccobeats", "essentia_lowlevel"),
}

# ReccoBeats-first fields with local TensorFlow / derived fallbacks (phase 6).
_ADVANCED_FALLBACK: dict[str, str] = {
    "energy": "energy_proxy",
    "danceability": "danceability_tf",
    "valence": "valence_tf",
    "acousticness": "acoustic_profile_score",
    "instrumentalness": "instrumental_focus_score",
}

_CONSUMER_PHASE = 5


class FeatureResolver:
    """Load normalized TrackFeatureView rows for playlist engine consumers."""

    def __init__(
        self,
        *,
        registry: FeatureRegistry | None = None,
        features_repo: AudioFeaturesRepository | None = None,
        advanced_repo: TrackAdvancedFeaturesRepository | None = None,
        embeddings_repo: TrackEmbeddingsRepository | None = None,
    ) -> None:
        self._registry = registry or get_feature_registry()
        self._features = features_repo or AudioFeaturesRepository()
        self._advanced = advanced_repo or TrackAdvancedFeaturesRepository()
        self._embeddings = embeddings_repo or TrackEmbeddingsRepository()
        self._sources = FeatureSourcesRepository()

    def load_views(self, session: Session, track_ids: list[int]) -> dict[int, TrackFeatureView]:
        if not track_ids:
            return {}
        unique_ids = sorted(set(track_ids))
        tracks = self._load_tracks(session, unique_ids)
        source_by_name = self._load_source_map(session)
        active_features = self._load_active_features(session, unique_ids)
        previews = self._load_previews(session, unique_ids)
        liked = self._load_liked(session, unique_ids)
        playlist_map = self._load_playlist_ids(session, unique_ids)
        isrc_map = self._load_isrc(session, unique_ids)
        advanced_by_track = self._load_advanced_features(session, unique_ids)
        embeddings_by_track = self._load_embeddings(session, unique_ids)

        out: dict[int, TrackFeatureView] = {}
        for tid in unique_ids:
            track_row = tracks.get(tid)
            if track_row is None:
                continue
            out[tid] = self._build_view(
                session,
                track_row,
                active_features.get(tid, {}),
                source_by_name,
                preview=previews.get(tid),
                liked=liked.get(tid, False),
                playlist_ids=playlist_map.get(tid, []),
                isrc=isrc_map.get(tid),
                advanced_by_name=advanced_by_track.get(tid, {}),
                embedding_row=embeddings_by_track.get(tid),
            )
        return out

    def _load_embeddings(
        self, session: Session, track_ids: list[int]
    ) -> dict[int, TrackEmbedding]:
        rows = self._embeddings.list_for_tracks(session, track_ids)
        out: dict[int, TrackEmbedding] = {}
        for row in rows:
            if row.status not in ("success", "partial"):
                continue
            existing = out.get(row.track_id)
            if existing is None:
                out[row.track_id] = row
        return out

    def _load_advanced_features(
        self, session: Session, track_ids: list[int]
    ) -> dict[int, dict[str, TrackAdvancedFeature]]:
        rows = self._advanced.list_for_tracks(session, track_ids)
        out: dict[int, dict[str, TrackAdvancedFeature]] = {}
        for row in rows:
            bucket = out.setdefault(row.track_id, {})
            existing = bucket.get(row.feature_name)
            if existing is None or self._advanced_row_precedence(row, existing):
                bucket[row.feature_name] = row
        return out

    @staticmethod
    def _advanced_row_precedence(
        candidate: TrackAdvancedFeature, current: TrackAdvancedFeature
    ) -> bool:
        priority = {"success": 3, "partial": 2, "model_missing": 1, "missing": 0, "failed": 0}
        return priority.get(candidate.status, 0) >= priority.get(current.status, 0)

    def _feature_value_from_advanced(
        self, row: TrackAdvancedFeature, *, feature_name: str | None = None
    ) -> FeatureValue:
        name = feature_name or row.feature_name
        warnings: list[str] = []
        if row.model_name:
            warnings.append(f"model_name={row.model_name}")
        if row.pipeline_version:
            warnings.append(f"pipeline_version={row.pipeline_version}")

        if row.status == "model_missing":
            return FeatureValue(
                name=name,
                status="model_missing",  # type: ignore[arg-type]
                missing_reason="MODEL_MISSING",
                source=row.source,
                warnings=warnings,
            )
        value: Any = row.value_float
        if row.feature_name == "genre_discogs_519_top_k" and row.value_json:
            try:
                value = json.loads(row.value_json)
            except json.JSONDecodeError:
                value = None
        elif row.feature_name == "genre_discogs_519" and row.value_json:
            try:
                value = json.loads(row.value_json)
            except json.JSONDecodeError:
                value = None
        elif row.value_text is not None:
            value = row.value_text

        if value is None:
            return FeatureValue(
                name=name,
                status="missing",
                missing_reason="FEATURE_MISSING",
                source=row.source,
                warnings=warnings,
            )

        status: str = "available"
        missing_reason = None
        if row.status == "partial":
            status = "low_confidence"
            missing_reason = "FEATURE_LOW_CONFIDENCE"
        elif row.status not in ("success", "partial"):
            status = "missing"
            missing_reason = "FEATURE_MISSING"

        conf = row.confidence
        if conf is not None and conf < _LOW_CONFIDENCE_THRESHOLD and status == "available":
            status = "low_confidence"
            missing_reason = "FEATURE_LOW_CONFIDENCE"

        numeric_value = value
        if isinstance(value, (int, float)):
            numeric_value = float(value)

        return FeatureValue(
            name=name,
            value=numeric_value if isinstance(numeric_value, float) else value,
            confidence=conf,
            source=row.source,
            status=status,  # type: ignore[arg-type]
            missing_reason=missing_reason,
            warnings=warnings,
        )

    def _load_tracks(self, session: Session, track_ids: list[int]) -> dict[int, tuple]:
        stmt = (
            select(
                Track,
                SpotifyTrack,
                Album.name,
            )
            .outerjoin(SpotifyTrack, SpotifyTrack.track_id == Track.id)
            .outerjoin(Album, Album.id == SpotifyTrack.album_id)
            .where(Track.id.in_(track_ids))
        )
        rows = session.execute(stmt).all()
        artists = self._load_artists(session, track_ids)
        result: dict[int, tuple] = {}
        for track, sp, album_name in rows:
            result[track.id] = (track, sp, album_name, artists.get(track.id, ([], [])))
        return result

    def _load_artists(
        self, session: Session, track_ids: list[int]
    ) -> dict[int, tuple[list[str], list[int]]]:
        stmt = (
            select(TrackArtist.track_id, Artist.id, Artist.name)
            .join(Artist, Artist.id == TrackArtist.artist_id)
            .where(TrackArtist.track_id.in_(track_ids))
            .order_by(TrackArtist.position)
        )
        out: dict[int, tuple[list[str], list[int]]] = {}
        for tid, aid, name in session.execute(stmt).all():
            names, ids = out.setdefault(tid, ([], []))
            names.append(name)
            ids.append(aid)
        return out

    def _load_source_map(self, session: Session) -> dict[str, FeatureSource]:
        rows = session.execute(select(FeatureSource)).scalars().all()
        return {r.name: r for r in rows}

    def _load_active_features(
        self, session: Session, track_ids: list[int]
    ) -> dict[int, dict[str, AudioFeature]]:
        stmt = select(AudioFeature, FeatureSource.name).join(
            FeatureSource, FeatureSource.id == AudioFeature.feature_source_id
        ).where(
            AudioFeature.track_id.in_(track_ids),
            AudioFeature.is_active.is_(True),
        )
        out: dict[int, dict[str, AudioFeature]] = {}
        for row, source_name in session.execute(stmt).all():
            out.setdefault(row.track_id, {})[source_name] = row
        return out

    def _load_previews(self, session: Session, track_ids: list[int]) -> dict[int, bool]:
        stmt = select(TrackPreview.track_id).where(
            TrackPreview.track_id.in_(track_ids),
            TrackPreview.provider == "deezer",
            TrackPreview.preview_url.isnot(None),
        )
        return {tid: True for (tid,) in session.execute(stmt).all()}

    def _load_liked(self, session: Session, track_ids: list[int]) -> dict[int, bool]:
        stmt = (
            select(SpotifyTrack.track_id)
            .join(LikedTrack, LikedTrack.spotify_track_id == SpotifyTrack.spotify_track_id)
            .where(
                SpotifyTrack.track_id.in_(track_ids),
                LikedTrack.is_current.is_(True),
            )
        )
        return {tid: True for (tid,) in session.execute(stmt).all()}

    def _load_playlist_ids(self, session: Session, track_ids: list[int]) -> dict[int, list[int]]:
        stmt = (
            select(SpotifyTrack.track_id, Playlist.id)
            .join(PlaylistTrack, PlaylistTrack.spotify_track_id == SpotifyTrack.spotify_track_id)
            .join(Playlist, Playlist.spotify_playlist_id == PlaylistTrack.spotify_playlist_id)
            .where(
                SpotifyTrack.track_id.in_(track_ids),
                PlaylistTrack.is_current.is_(True),
            )
        )
        out: dict[int, list[int]] = {}
        for tid, pid in session.execute(stmt).all():
            out.setdefault(tid, []).append(pid)
        return out

    def _load_isrc(self, session: Session, track_ids: list[int]) -> dict[int, str]:
        stmt = select(ExternalId.track_id, ExternalId.id_value).where(
            ExternalId.track_id.in_(track_ids),
            ExternalId.id_type == "isrc",
        )
        return {tid: val for tid, val in session.execute(stmt).all()}

    def _pick_primary_row(
        self, by_source: dict[str, AudioFeature]
    ) -> tuple[AudioFeature | None, str | None]:
        for source_name in ("reccobeats", "essentia_lowlevel"):
            row = by_source.get(source_name)
            if row is not None:
                return row, source_name
        if by_source:
            name = next(iter(by_source))
            return by_source[name], name
        return None, None

    def _apply_advanced_features(
        self,
        features: dict[str, FeatureValue],
        advanced_by_name: dict[str, TrackAdvancedFeature],
    ) -> None:
        for canonical, advanced_name in _ADVANCED_FALLBACK.items():
            current = features.get(canonical)
            if (
                current is not None
                and current.status == "available"
                and current.value is not None
            ):
                continue
            row = advanced_by_name.get(advanced_name)
            if row is None:
                continue
            features[canonical] = self._feature_value_from_advanced(
                row, feature_name=canonical
            )

        for name, row in advanced_by_name.items():
            if name in features:
                continue
            desc = self._registry.get(name)
            if desc is None or desc.phase_available != 6:
                continue
            features[name] = self._feature_value_from_advanced(row)

    def _apply_embedding_features(
        self,
        features: dict[str, FeatureValue],
        embedding_row: TrackEmbedding | None,
    ) -> None:
        if embedding_row is None:
            return
        try:
            vector = self._embeddings.parse_vector(embedding_row)
        except (json.JSONDecodeError, ValueError):
            return

        warnings: list[str] = [
            f"model_name={embedding_row.model_name}",
            f"pipeline_version={embedding_row.pipeline_version or ''}",
        ]
        conf = embedding_row.confidence
        status: str = "available"
        if embedding_row.status == "partial":
            status = "low_confidence"
        elif embedding_row.status != "success":
            status = "missing"

        features["style_embedding"] = FeatureValue(
            name="style_embedding",
            value=vector,
            confidence=conf,
            source="track_embeddings",
            status=status,  # type: ignore[arg-type]
            warnings=[w for w in warnings if w],
        )
        timbre = vector[:TIMBRE_EMBEDDING_DIM]
        features["timbre_embedding"] = FeatureValue(
            name="timbre_embedding",
            value=timbre,
            confidence=conf,
            source="track_embeddings",
            status=status,  # type: ignore[arg-type]
            warnings=warnings + [f"timbre_dims={len(timbre)}"],
        )

    def _pick_row(
        self,
        field: str,
        by_source: dict[str, AudioFeature],
    ) -> tuple[AudioFeature | None, str | None]:
        for source_name in _FIELD_SOURCE_PRIORITY.get(field, ("reccobeats", "essentia_lowlevel")):
            row = by_source.get(source_name)
            if row is None:
                continue
            val = getattr(row, field, None)
            if val is not None:
                return row, source_name
        for source_name, row in by_source.items():
            val = getattr(row, field, None)
            if val is not None:
                return row, source_name
        return None, None

    def _build_view(
        self,
        session: Session,
        track_bundle: tuple,
        by_source: dict[str, AudioFeature],
        source_by_name: dict[str, FeatureSource],
        *,
        preview: bool | None,
        liked: bool,
        playlist_ids: list[int],
        isrc: str | None,
        advanced_by_name: dict[str, TrackAdvancedFeature],
        embedding_row: TrackEmbedding | None = None,
    ) -> TrackFeatureView:
        track, sp, album_name, (artist_names, artist_ids) = track_bundle
        sp_id = sp.spotify_track_id if sp else None
        album_id = sp.album_id if sp else None
        market_status = sp.market_status if sp else "unknown"
        if sp and sp.is_playable is False:
            availability = "unavailable"
        elif sp and sp.is_playable is True:
            availability = "available"
        else:
            availability = market_status if market_status != "unknown" else "unknown"

        features: dict[str, FeatureValue] = {}

        for name in FEATURE_FIELD_NAMES:
            row, src_name = self._pick_row(name, by_source)
            if row is None:
                features[name] = FeatureValue(
                    name=name,
                    status="missing",
                    missing_reason="FEATURE_MISSING",
                )
                continue
            raw_val = getattr(row, name, None)
            conf_attr = f"{name}_confidence" if name != "feature_confidence" else None
            field_conf = getattr(row, conf_attr, None) if conf_attr else None
            if name == "feature_confidence":
                field_conf = row.feature_confidence
            fc = field_confidence(name, raw_val, match_confidence=field_conf or 1.0)
            status: str = "available"
            missing_reason = None
            warnings: list[str] = []
            if fc.value is None:
                status = "missing"
                missing_reason = "FEATURE_MISSING"
            elif fc.confidence is not None and fc.confidence < _LOW_CONFIDENCE_THRESHOLD:
                status = "low_confidence"
                missing_reason = "FEATURE_LOW_CONFIDENCE"
            src_row = source_by_name.get(src_name or "")
            features[name] = FeatureValue(
                name=name,
                value=fc.value,
                confidence=fc.confidence,
                source=src_name,
                source_version=src_row.version if src_row else None,
                status=status,  # type: ignore[arg-type]
                missing_reason=missing_reason,
                warnings=warnings,
            )

        # Row-level aggregate confidence (not a per-field column in FEATURE_FIELD_NAMES).
        primary_row, primary_src = self._pick_primary_row(by_source)
        if primary_row is not None and primary_row.feature_confidence is not None:
            agg_conf = float(primary_row.feature_confidence)
            features["feature_confidence"] = FeatureValue(
                name="feature_confidence",
                value=agg_conf,
                confidence=agg_conf,
                source=primary_src,
                source_version=source_by_name.get(primary_src or "").version
                if primary_src and source_by_name.get(primary_src)
                else None,
                status="available" if agg_conf >= _LOW_CONFIDENCE_THRESHOLD else "low_confidence",
                missing_reason=None
                if agg_conf >= _LOW_CONFIDENCE_THRESHOLD
                else "FEATURE_LOW_CONFIDENCE",
            )
        else:
            features["feature_confidence"] = FeatureValue(
                name="feature_confidence",
                status="missing",
                missing_reason="FEATURE_MISSING",
            )

        # Derived alias valence_inverse
        val = features.get("valence")
        if val and val.value is not None and isinstance(val.value, (int, float)):
            inv = 1.0 - float(val.value)
            features["valence_inverse"] = FeatureValue(
                name="valence_inverse",
                value=inv,
                confidence=val.confidence,
                source=val.source,
                source_version=val.source_version,
                status="available",
            )

        features["preview_available"] = FeatureValue(
            name="preview_available",
            value=bool(preview),
            status="available",
            source="track_previews",
        )
        features["availability_status"] = FeatureValue(
            name="availability_status",
            value=availability,
            status="available",
            source="metadata",
        )
        features["market_status"] = FeatureValue(
            name="market_status",
            value=market_status,
            status="available",
            source="metadata",
        )
        features["liked_status"] = FeatureValue(
            name="liked_status",
            value=liked,
            status="available",
            source="metadata",
        )
        features["playlist_membership"] = FeatureValue(
            name="playlist_membership",
            value=playlist_ids,
            status="available",
            source="metadata",
        )
        features["isrc"] = FeatureValue(
            name="isrc",
            value=isrc,
            status="available" if isrc else "missing",
            missing_reason=None if isrc else "FEATURE_MISSING",
            source="metadata",
        )
        features["artist_id"] = FeatureValue(
            name="artist_id",
            value=artist_ids[0] if artist_ids else None,
            status="available" if artist_ids else "missing",
            source="metadata",
        )
        features["album_id"] = FeatureValue(
            name="album_id",
            value=album_id,
            status="available" if album_id else "missing",
            source="metadata",
        )
        features["duplicate_status"] = FeatureValue(
            name="duplicate_status",
            value="unique",
            status="not_applicable",
            source="metadata",
        )

        self._apply_embedding_features(features, embedding_row)
        self._apply_advanced_features(features, advanced_by_name)

        for desc in self._registry.list_all_descriptors():
            if desc.phase_available <= _CONSUMER_PHASE or desc.name in features:
                continue
            if desc.name in advanced_by_name:
                features[desc.name] = self._feature_value_from_advanced(
                    advanced_by_name[desc.name]
                )
                continue
            if desc.phase_available > 6:
                features[desc.name] = FeatureValue(
                    name=desc.name,
                    status="not_available_yet",
                    missing_reason="FEATURE_NOT_AVAILABLE_YET",
                    warnings=["FEATURE_NOT_AVAILABLE_YET"],
                )
            else:
                features[desc.name] = FeatureValue(
                    name=desc.name,
                    status="missing",
                    missing_reason="FEATURE_MISSING",
                )

        return TrackFeatureView(
            track_id=track.id,
            spotify_track_id=sp_id,
            title=track.name,
            artist_names=artist_names,
            artist_ids=artist_ids,
            album_id=album_id,
            album_name=album_name,
            isrc=isrc,
            duration_ms=track.duration_ms,
            availability_status=availability,
            market_status=market_status,
            liked=liked,
            playlist_ids=playlist_ids,
            duplicate_status="unique",
            preview_available=bool(preview),
            features=features,
        )
