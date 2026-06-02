from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_library import Artist, TrackArtist
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.features.schemas import (
    CoverageFieldOut,
    CoverageResponse,
    CoverageSourceOut,
    CoverageSummaryOut,
    FailurePageOut,
    RecentFailureOut,
)

COVERAGE_FIELDS = (
    "bpm",
    "energy",
    "danceability",
    "valence",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "liveness",
    "loudness",
    "key",
    "mode",
)


class FeatureCoverageService:
    def __init__(
        self,
        *,
        features_repo: AudioFeaturesRepository | None = None,
        sources_repo: FeatureSourcesRepository | None = None,
    ) -> None:
        self._features = features_repo or AudioFeaturesRepository()
        self._sources = sources_repo or FeatureSourcesRepository()

    def get_coverage(
        self,
        session: Session,
        *,
        source: str = "all",
        include_failed: bool = True,
        include_fields: bool = True,
        recent_failures_limit: int = 20,
        failures_page: int = 1,
        failures_page_size: int = 20,
    ) -> CoverageResponse:
        track_count = self._features.count_tracks_total(session)
        sources_out: list[CoverageSourceOut] = []

        if source == "all":
            source_rows = self._sources.list_all(session)
        else:
            row = self._sources.get_by_name(session, source)
            source_rows = [row] if row else []

        with_any = 0
        with_reccobeats = 0
        missing_reccobeats = track_count
        failed_reccobeats = 0
        not_found_reccobeats = 0
        with_essentia = 0
        missing_essentia = track_count
        failed_essentia = 0
        not_found_essentia = 0

        reccobeats_source = self._sources.get_by_name(session, "reccobeats")
        essentia_source = self._sources.get_by_name(session, "essentia_lowlevel")
        fields_out: list[CoverageFieldOut] = []
        recent_failures: list[RecentFailureOut] = []
        failures_page_out: FailurePageOut | None = None

        for src in source_rows:
            if src is None:
                continue
            src_id = src.id
            success = self._features.count_by_status(
                session, feature_source_id=src_id, status="success"
            )
            partial = self._features.count_by_status(
                session, feature_source_id=src_id, status="partial"
            )
            failed = self._features.count_by_status(
                session, feature_source_id=src_id, status="failed"
            )
            not_found = self._features.count_by_status(
                session, feature_source_id=src_id, status="not_found"
            )
            covered = success + partial
            missing = max(0, track_count - covered)
            coverage_pct = (covered / track_count * 100.0) if track_count else 0.0

            sources_out.append(
                CoverageSourceOut(
                    source=src.name,
                    active=src.is_active,
                    version=src.version,
                    track_count=track_count,
                    success_count=success,
                    missing_count=missing,
                    failed_count=failed,
                    not_found_count=not_found,
                    partial_count=partial,
                    coverage_percent=round(coverage_pct, 2),
                )
            )

            if src.name == "reccobeats":
                with_reccobeats = covered
                missing_reccobeats = missing
                failed_reccobeats = failed
                not_found_reccobeats = not_found
                if include_fields:
                    for field_name in COVERAGE_FIELDS:
                        available = self._features.count_field_available(
                            session, feature_source_id=src.id, field_name=field_name
                        )
                        pct = (available / track_count * 100.0) if track_count else 0.0
                        fields_out.append(
                            CoverageFieldOut(
                                field=field_name,
                                available_count=available,
                                coverage_percent=round(pct, 2),
                            )
                        )
            if src.name == "essentia_lowlevel":
                with_essentia = covered
                missing_essentia = missing
                failed_essentia = failed
                not_found_essentia = not_found

        if include_failed:
            failure_source_ids = [s.id for s in source_rows if s is not None]
            if failure_source_ids:
                recent_failures = self._build_recent_failures_multi(
                    session, feature_source_ids=failure_source_ids, limit=recent_failures_limit
                )
                total = self._features.count_failures(
                    session, feature_source_ids=failure_source_ids
                )
                page = max(1, int(failures_page))
                page_size = max(1, min(int(failures_page_size), 200))
                offset = (page - 1) * page_size
                rows = self._features.list_failures_page(
                    session,
                    feature_source_ids=failure_source_ids,
                    offset=offset,
                    limit=page_size,
                )
                items: list[RecentFailureOut] = []
                for feature, track, src in rows:
                    artist_names = self._artist_names(session, track.id)
                    items.append(
                        RecentFailureOut(
                            source=src.name,
                            track_id=track.id,
                            title=track.name,
                            artist_names=artist_names,
                            status=feature.status,
                            error_code=feature.error_code,
                            error_message=feature.error_message,
                        )
                    )
                failures_page_out = FailurePageOut(
                    total=total, page=page, page_size=page_size, items=items
                )

        if reccobeats_source:
            with_any = self._features.count_with_active_source(
                session,
                feature_source_id=reccobeats_source.id,
                statuses=("success", "partial"),
            )

        summary_pct = (with_reccobeats / track_count * 100.0) if track_count else 0.0
        summary = CoverageSummaryOut(
            track_count=track_count,
            with_any_features=with_any,
            with_reccobeats=with_reccobeats,
            missing_reccobeats=missing_reccobeats,
            failed_reccobeats=failed_reccobeats,
            not_found_reccobeats=not_found_reccobeats,
            with_essentia_lowlevel=with_essentia,
            missing_essentia_lowlevel=missing_essentia,
            failed_essentia_lowlevel=failed_essentia,
            not_found_essentia_lowlevel=not_found_essentia,
            coverage_percent=round(summary_pct, 2),
        )

        return CoverageResponse(
            summary=summary,
            sources=sources_out,
            fields=fields_out,
            recent_failures=recent_failures,
            failures=failures_page_out,
        )

    def _build_recent_failures(
        self, session: Session, *, feature_source_id: int, limit: int
    ) -> list[RecentFailureOut]:
        rows = self._features.list_recent_failures(
            session, feature_source_id=feature_source_id, limit=limit
        )
        out: list[RecentFailureOut] = []
        for feature, track in rows:
            artist_names = self._artist_names(session, track.id)
            out.append(
                RecentFailureOut(
                    track_id=track.id,
                    title=track.name,
                    artist_names=artist_names,
                    status=feature.status,
                    error_code=feature.error_code,
                    error_message=feature.error_message,
                )
            )
        return out

    def _build_recent_failures_multi(
        self, session: Session, *, feature_source_ids: list[int], limit: int
    ) -> list[RecentFailureOut]:
        # Keep this "recent failures" list simple/short for header cards (legacy UI).
        rows = self._features.list_failures_page(
            session, feature_source_ids=feature_source_ids, offset=0, limit=limit
        )
        out: list[RecentFailureOut] = []
        for feature, track, src in rows:
            artist_names = self._artist_names(session, track.id)
            out.append(
                RecentFailureOut(
                    source=src.name,
                    track_id=track.id,
                    title=track.name,
                    artist_names=artist_names,
                    status=feature.status,
                    error_code=feature.error_code,
                    error_message=feature.error_message,
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
        return list(session.execute(q).scalars())
