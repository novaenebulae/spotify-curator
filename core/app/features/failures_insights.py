from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_audio import AudioDownloadJob
from app.database.models_features import AudioFeature
from app.database.models_library import Artist, Track, TrackArtist
from app.database.models_previews import TrackPreview
from app.database.repositories.audio_features import AudioFeaturesRepository
from app.features.schemas import FailurePageOut, RecentFailureOut


@dataclass(frozen=True)
class _FailureRow:
    source: str
    track_id: int
    title: str
    artist_names: list[str]
    status: str
    error_code: str | None
    error_message: str | None
    occurred_at: datetime


class FailureInsightsService:
    def __init__(self, *, features_repo: AudioFeaturesRepository | None = None) -> None:
        self._features = features_repo or AudioFeaturesRepository()

    def list_failures_page(
        self,
        session: Session,
        *,
        feature_source_ids: list[int],
        failures_after: datetime | None,
        offset: int,
        limit: int,
        max_per_source: int = 300,
    ) -> FailurePageOut:
        records = self._collect_all(
            session,
            feature_source_ids=feature_source_ids,
            failures_after=failures_after,
            max_per_source=max_per_source,
        )
        records.sort(key=lambda r: r.occurred_at, reverse=True)
        total = len(records)
        page_items = records[offset : offset + limit]
        items = [
            RecentFailureOut(
                source=r.source,
                track_id=r.track_id,
                title=r.title,
                artist_names=r.artist_names,
                status=r.status,
                error_code=r.error_code,
                error_message=r.error_message,
                occurred_at=r.occurred_at.isoformat() if r.occurred_at else None,
            )
            for r in page_items
        ]
        page = (offset // limit) + 1 if limit else 1
        return FailurePageOut(total=total, page=page, page_size=limit, items=items)

    def list_recent(
        self,
        session: Session,
        *,
        feature_source_ids: list[int],
        failures_after: datetime | None,
        limit: int,
    ) -> list[RecentFailureOut]:
        page = self.list_failures_page(
            session,
            feature_source_ids=feature_source_ids,
            failures_after=failures_after,
            offset=0,
            limit=limit,
        )
        return page.items

    def _collect_all(
        self,
        session: Session,
        *,
        feature_source_ids: list[int],
        failures_after: datetime | None,
        max_per_source: int,
    ) -> list[_FailureRow]:
        out: list[_FailureRow] = []
        if feature_source_ids:
            rows = self._features.list_failures_page(
                session,
                feature_source_ids=feature_source_ids,
                offset=0,
                limit=max_per_source,
            )
            for feature, track, src in rows:
                occurred = feature.fetched_at or feature.updated_at or datetime.utcnow()
                if failures_after and occurred <= failures_after:
                    continue
                out.append(
                    _FailureRow(
                        source=src.name,
                        track_id=track.id,
                        title=track.name,
                        artist_names=self._artist_names(session, track.id),
                        status=feature.status,
                        error_code=feature.error_code,
                        error_message=feature.error_message,
                        occurred_at=occurred,
                    )
                )

        preview_rows = session.execute(
            select(TrackPreview, Track)
            .join(Track, Track.id == TrackPreview.track_id)
            .where(
                TrackPreview.provider == "deezer",
                TrackPreview.is_available.is_(False),
                TrackPreview.last_error.is_not(None),
            )
            .order_by(TrackPreview.updated_at.desc().nullslast())
            .limit(max_per_source)
        ).all()
        for preview, track in preview_rows:
            occurred = preview.updated_at or preview.last_checked_at or datetime.utcnow()
            if failures_after and occurred <= failures_after:
                continue
            out.append(
                _FailureRow(
                    source="deezer_preview",
                    track_id=track.id,
                    title=track.name,
                    artist_names=self._artist_names(session, track.id),
                    status="failed",
                    error_code="PREVIEW_UNAVAILABLE",
                    error_message=(preview.last_error or "")[:2000] or None,
                    occurred_at=occurred,
                )
            )

        dl_rows = session.execute(
            select(AudioDownloadJob, Track)
            .join(Track, Track.id == AudioDownloadJob.track_id)
            .where(AudioDownloadJob.status == "failed")
            .order_by(AudioDownloadJob.finished_at.desc().nullslast())
            .limit(max_per_source)
        ).all()
        for dl, track in dl_rows:
            occurred = dl.finished_at or dl.created_at
            if failures_after and occurred <= failures_after:
                continue
            out.append(
                _FailureRow(
                    source="audio_download",
                    track_id=track.id,
                    title=track.name,
                    artist_names=self._artist_names(session, track.id),
                    status="failed",
                    error_code="DOWNLOAD_FAILED",
                    error_message=(dl.last_error or "")[:2000] or None,
                    occurred_at=occurred,
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
