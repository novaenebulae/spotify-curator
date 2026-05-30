from __future__ import annotations

import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_library import SpotifyTrack
from app.database.repositories.tracks import ALLOWED_SORT_FIELDS, TracksRepository
from app.library.diff import diff_snapshots
from app.library.schemas import (
    PaginationOut,
    SortOut,
    TrackAlbumOut,
    TrackArtistOut,
    TrackListItem,
    TrackListResponse,
    TrackSearchFilters,
)
from app.library.snapshots import SnapshotService
from app.observability.errors import ApiError
from app.observability.sql_perf import (
    perf_segment,
    track_search_perf_context,
    tracks_perf_logging_enabled,
)


class TrackSearchService:
    def __init__(self) -> None:
        self._repo = TracksRepository()
        self._snapshots = SnapshotService()

    def search(self, filters: TrackSearchFilters) -> TrackListResponse:
        if filters.sort not in ALLOWED_SORT_FIELDS:
            raise ApiError(
                code="VALIDATION_ERROR",
                message=f"Invalid sort field: {filters.sort}",
                status_code=400,
            )
        if filters.order not in ("asc", "desc"):
            raise ApiError(
                code="VALIDATION_ERROR",
                message="order must be asc or desc",
                status_code=400,
            )

        page = max(1, filters.page)
        page_size = min(200, max(1, filters.page_size))

        filter_dict = filters.model_dump(exclude_none=True)
        filter_dict["sort"] = filters.sort
        filter_dict["order"] = filters.order

        engine = get_engine()
        perf_ctx = track_search_perf_context() if tracks_perf_logging_enabled() else None
        perf_manager = perf_ctx if perf_ctx is not None else _noop_perf()
        with perf_manager as perf:
            with Session(engine) as session:
                snapshot_track_ids = None
                if filters.snapshot_status:
                    snapshot_track_ids = self._track_ids_for_snapshot_status(
                        session, filters.snapshot_status
                    )

                duplicate_track_ids = None
                if filters.duplicate_status:
                    duplicate_track_ids = self._repo.duplicate_isrc_track_ids(session)

                ids_query = self._repo.build_ids_query(
                    session,
                    filters=filter_dict,
                    snapshot_track_ids=snapshot_track_ids,
                    duplicate_track_ids=duplicate_track_ids,
                )
                with perf_segment(perf, "count_ms"):
                    total = self._repo.count(
                        session,
                        filters=filter_dict,
                        snapshot_track_ids=snapshot_track_ids,
                        duplicate_track_ids=duplicate_track_ids,
                    )
                offset = (page - 1) * page_size
                with perf_segment(perf, "page_ids_ms"):
                    rows = self._repo.fetch_page(
                        session, ids_query, offset=offset, limit=page_size
                    )

                track_ids = [r.track_id for r in rows]
                sp_ids = [r.spotify_track_id for r in rows]
                with perf_segment(perf, "artists_ms"):
                    artists_map = self._repo.fetch_artists_for_tracks(session, track_ids)
                album_ids = [r.album_id for r in rows if r.album_id]
                with perf_segment(perf, "albums_ms"):
                    albums_map = self._repo.fetch_albums_for_tracks(session, album_ids)
                with perf_segment(perf, "playlists_ms"):
                    playlist_counts = self._repo.fetch_playlist_counts_for_tracks(
                        session, sp_ids
                    )

                dup_ids = duplicate_track_ids or set()
                items: list[TrackListItem] = []
                for row in rows:
                    artists = artists_map.get(row.track_id, [])
                    album = albums_map.get(row.album_id) if row.album_id else None
                    pl_count = playlist_counts.get(row.spotify_track_id, 0)
                    dup_status = "none"
                    if row.track_id in dup_ids:
                        if filters.duplicate_status == "confirmed":
                            dup_status = "confirmed"
                        else:
                            dup_status = "potential"

                    items.append(
                        TrackListItem(
                            track_id=row.track_id,
                            spotify_track_id=row.spotify_track_id,
                            spotify_uri=row.spotify_uri,
                            title=row.title,
                            normalized_title=row.normalized_title,
                            artists=[TrackArtistOut(**a) for a in artists],
                            artist_names=[a["name"] for a in artists],
                            album=TrackAlbumOut(**album) if album else None,
                            duration_ms=row.duration_ms,
                            explicit=row.explicit,
                            popularity=row.popularity,
                            isrc=row.isrc,
                            liked=row.liked,
                            liked_added_at=row.liked_added_at,
                            is_current_liked=row.is_current_liked,
                            playlist_count=pl_count,
                            playlists=[],
                            availability_status=row.market_status,
                            market_status=row.market_status,
                            duplicate_status=dup_status,
                            last_seen_at=row.last_seen_at,
                            external_url=row.external_url,
                            preview_url=row.preview_url,
                        )
                    )

        total_pages = math.ceil(total / page_size) if total else 0
        active_filters = {
            k: v
            for k, v in filters.model_dump().items()
            if v is not None and k not in ("page", "page_size", "sort", "order")
        }

        return TrackListResponse(
            items=items,
            pagination=PaginationOut(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
            ),
            sort=SortOut(field=filters.sort, order=filters.order),
            filters=active_filters,
        )

    def _track_ids_for_snapshot_status(self, session: Session, status: str) -> set[int]:
        snapshots = self._snapshots.list_snapshots()
        if len(snapshots) < 2:
            return set()
        to_id = snapshots[0]["id"]
        from_id = snapshots[1]["id"]
        diff = diff_snapshots(from_id, to_id)
        spotify_ids = {
            item["spotify_track_id"]
            for item in diff["tracks"]["statuses"]
            if item.get("status") == status and item.get("spotify_track_id")
        }
        if not spotify_ids:
            return set()
        stmt = select(SpotifyTrack.track_id).where(SpotifyTrack.spotify_track_id.in_(spotify_ids))
        return set(session.execute(stmt).scalars().all())

    def search_track_ids(
        self,
        filters: dict[str, Any],
        *,
        limit: int = 500,
    ) -> list[int]:
        """Resolve track IDs for dry-run filter-based actions."""
        engine = get_engine()
        with Session(engine) as session:
            filter_dict = dict(filters)
            filter_dict.setdefault("sort", "title")
            filter_dict.setdefault("order", "asc")
            ids_query = self._repo.build_ids_query(session, filters=filter_dict)
            return list(session.execute(ids_query.limit(limit)).scalars().all())


class _noop_perf:
    def __enter__(self):
        from app.observability.sql_perf import TrackSearchPerf

        return TrackSearchPerf()

    def __exit__(self, *args: object) -> None:
        return None
