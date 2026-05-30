from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.database.models_library import (
    Album,
    Artist,
    ExternalId,
    LikedTrack,
    SpotifyAlbum,
    SpotifyArtist,
    SpotifyTrack,
    Track,
    TrackArtist,
)
from app.database.models_playlists import Playlist, PlaylistTrack
from app.library.normalize import normalize_text


@dataclass(frozen=True)
class TrackRow:
    track_id: int
    spotify_track_id: str
    spotify_uri: str
    title: str
    normalized_title: str
    duration_ms: int
    explicit: bool
    popularity: int | None
    preview_url: str | None
    external_url: str | None
    market_status: str
    is_playable: bool | None
    last_seen_at: datetime | None
    album_id: int | None
    liked: bool
    liked_added_at: datetime | None
    is_current_liked: bool
    isrc: str | None


ALLOWED_SORT_FIELDS = frozenset(
    {
        "title",
        "artist",
        "album",
        "duration_ms",
        "liked_added_at",
        "popularity",
        "last_seen_at",
        "playlist_count",
    }
)


def _primary_artist_subq():
    return (
        select(Artist.normalized_name)
        .select_from(TrackArtist)
        .join(Artist, TrackArtist.artist_id == Artist.id)
        .where(TrackArtist.track_id == Track.id, TrackArtist.position == 0)
        .correlate(Track)
        .scalar_subquery()
    )


def _playlist_count_subq():
    return (
        select(func.count(PlaylistTrack.id))
        .where(
            PlaylistTrack.spotify_track_id == SpotifyTrack.spotify_track_id,
            PlaylistTrack.is_current.is_(True),
        )
        .correlate(SpotifyTrack)
        .scalar_subquery()
    )


def _needs_album_join(filters: dict[str, Any], sort_field: str | None) -> bool:
    return bool(filters.get("q") or filters.get("album") or sort_field == "album")


def _needs_liked_join(filters: dict[str, Any], sort_field: str | None) -> bool:
    return (
        filters.get("liked") is not None
        or filters.get("added_after")
        or filters.get("added_before")
        or sort_field == "liked_added_at"
    )


def _needs_isrc_join(filters: dict[str, Any]) -> bool:
    return bool(filters.get("q") or filters.get("isrc"))


class TracksRepository:
    def _apply_joins(
        self,
        stmt: Select[Any],
        filters: dict[str, Any],
        *,
        sort_field: str | None = None,
    ) -> Select[Any]:
        stmt = stmt.select_from(Track).join(
            SpotifyTrack, SpotifyTrack.track_id == Track.id
        )
        if _needs_liked_join(filters, sort_field):
            stmt = stmt.outerjoin(
                LikedTrack,
                LikedTrack.spotify_track_id == SpotifyTrack.spotify_track_id,
            )
        if _needs_isrc_join(filters):
            stmt = stmt.outerjoin(
                ExternalId,
                and_(ExternalId.track_id == Track.id, ExternalId.id_type == "isrc"),
            )
        if _needs_album_join(filters, sort_field):
            stmt = stmt.outerjoin(Album, Album.id == SpotifyTrack.album_id)
        return stmt

    def _build_conditions(
        self,
        session: Session,
        filters: dict[str, Any],
        *,
        snapshot_track_ids: set[int] | None = None,
        duplicate_track_ids: set[int] | None = None,
    ) -> list[Any]:
        conditions: list[Any] = []

        q = filters.get("q")
        if q:
            term = f"%{normalize_text(q)}%"
            artist_exists = exists(
                select(1)
                .select_from(TrackArtist)
                .join(Artist, TrackArtist.artist_id == Artist.id)
                .where(
                    TrackArtist.track_id == Track.id,
                    Artist.normalized_name.like(term),
                )
            )
            q_parts: list[Any] = [
                Track.normalized_title.like(term),
                artist_exists,
            ]
            if _needs_album_join(filters, None):
                q_parts.append(Album.normalized_name.like(term))
            if _needs_isrc_join(filters):
                q_parts.append(ExternalId.id_value.like(f"%{q.strip()}%"))
            conditions.append(or_(*q_parts))

        if filters.get("title"):
            conditions.append(
                Track.normalized_title.like(f"%{normalize_text(filters['title'])}%")
            )
        if filters.get("artist"):
            term = f"%{normalize_text(filters['artist'])}%"
            conditions.append(
                exists(
                    select(1)
                    .select_from(TrackArtist)
                    .join(Artist, TrackArtist.artist_id == Artist.id)
                    .where(
                        TrackArtist.track_id == Track.id,
                        Artist.normalized_name.like(term),
                    )
                )
            )
        if filters.get("album"):
            conditions.append(
                Album.normalized_name.like(f"%{normalize_text(filters['album'])}%")
            )
        if filters.get("isrc"):
            conditions.append(ExternalId.id_value == filters["isrc"].strip())

        liked = filters.get("liked")
        if liked is True:
            conditions.append(LikedTrack.spotify_track_id.isnot(None))
        elif liked is False:
            conditions.append(LikedTrack.spotify_track_id.is_(None))

        playlist_id = filters.get("playlist_id")
        spotify_playlist_id = filters.get("spotify_playlist_id")
        if playlist_id is not None or spotify_playlist_id:
            pl_sub = select(Playlist.spotify_playlist_id).where(Playlist.id == playlist_id)
            if spotify_playlist_id:
                pl_id_val = spotify_playlist_id
            elif playlist_id is not None:
                pl_id_val = session.execute(pl_sub).scalar_one_or_none()
            else:
                pl_id_val = None
            if pl_id_val:
                conditions.append(
                    exists(
                        select(1).where(
                            PlaylistTrack.spotify_playlist_id == pl_id_val,
                            PlaylistTrack.spotify_track_id == SpotifyTrack.spotify_track_id,
                            PlaylistTrack.is_current.is_(True),
                        )
                    )
                )

        if filters.get("in_any_playlist") is True:
            conditions.append(
                exists(
                    select(1).where(
                        PlaylistTrack.spotify_track_id == SpotifyTrack.spotify_track_id,
                        PlaylistTrack.is_current.is_(True),
                    )
                )
            )
        elif filters.get("missing_from_playlists") is True:
            conditions.append(
                ~exists(
                    select(1).where(
                        PlaylistTrack.spotify_track_id == SpotifyTrack.spotify_track_id,
                        PlaylistTrack.is_current.is_(True),
                    )
                )
            )

        market_status = filters.get("market_status")
        if market_status:
            conditions.append(SpotifyTrack.market_status == market_status)

        availability = filters.get("availability_status")
        if availability:
            conditions.append(SpotifyTrack.market_status == availability)

        min_dur = filters.get("min_duration_ms")
        max_dur = filters.get("max_duration_ms")
        if min_dur is not None:
            conditions.append(Track.duration_ms >= min_dur)
        if max_dur is not None:
            conditions.append(Track.duration_ms <= max_dur)

        if filters.get("added_after"):
            conditions.append(LikedTrack.added_at >= filters["added_after"])
        if filters.get("added_before"):
            conditions.append(LikedTrack.added_at <= filters["added_before"])

        if snapshot_track_ids is not None:
            if snapshot_track_ids:
                conditions.append(Track.id.in_(snapshot_track_ids))
            else:
                conditions.append(Track.id == -1)

        if duplicate_track_ids is not None:
            dup_status = filters.get("duplicate_status")
            if dup_status and dup_status != "none":
                if duplicate_track_ids:
                    conditions.append(Track.id.in_(duplicate_track_ids))
                else:
                    conditions.append(Track.id == -1)
            elif dup_status == "none":
                if duplicate_track_ids:
                    conditions.append(~Track.id.in_(duplicate_track_ids))

        return conditions

    def build_count_query(
        self,
        session: Session,
        *,
        filters: dict[str, Any],
        snapshot_track_ids: set[int] | None = None,
        duplicate_track_ids: set[int] | None = None,
    ) -> Select[tuple[int]]:
        """COUNT without ORDER BY and with minimal joins for filters only."""
        stmt = select(func.count(Track.id))
        stmt = self._apply_joins(stmt, filters, sort_field=None)
        conditions = self._build_conditions(
            session,
            filters,
            snapshot_track_ids=snapshot_track_ids,
            duplicate_track_ids=duplicate_track_ids,
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt

    def build_ids_query(
        self,
        session: Session,
        *,
        filters: dict[str, Any],
        snapshot_track_ids: set[int] | None = None,
        duplicate_track_ids: set[int] | None = None,
    ) -> Select[tuple[int]]:
        sort_field = filters.get("sort") or "liked_added_at"
        stmt = select(Track.id)
        stmt = self._apply_joins(stmt, filters, sort_field=sort_field)
        conditions = self._build_conditions(
            session,
            filters,
            snapshot_track_ids=snapshot_track_ids,
            duplicate_track_ids=duplicate_track_ids,
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        order = (filters.get("order") or "desc").lower()
        desc = order == "desc"

        if sort_field == "title":
            col = Track.normalized_title
        elif sort_field == "artist":
            col = _primary_artist_subq()
        elif sort_field == "album":
            col = Album.normalized_name
        elif sort_field == "duration_ms":
            col = Track.duration_ms
        elif sort_field == "popularity":
            col = Track.popularity
        elif sort_field == "last_seen_at":
            col = SpotifyTrack.last_seen_at
        elif sort_field == "playlist_count":
            col = _playlist_count_subq()
        else:
            col = LikedTrack.added_at

        stmt = stmt.order_by(col.desc() if desc else col.asc(), Track.id.asc())
        return stmt

    def count(
        self,
        session: Session,
        *,
        filters: dict[str, Any],
        snapshot_track_ids: set[int] | None = None,
        duplicate_track_ids: set[int] | None = None,
    ) -> int:
        stmt = self.build_count_query(
            session,
            filters=filters,
            snapshot_track_ids=snapshot_track_ids,
            duplicate_track_ids=duplicate_track_ids,
        )
        return session.execute(stmt).scalar_one()

    def fetch_page(
        self,
        session: Session,
        ids_query: Select[tuple[int]],
        *,
        offset: int,
        limit: int,
    ) -> list[TrackRow]:
        page_ids = [
            row[0]
            for row in session.execute(ids_query.offset(offset).limit(limit)).all()
        ]
        if not page_ids:
            return []

        stmt = (
            select(
                Track.id,
                SpotifyTrack.spotify_track_id,
                SpotifyTrack.spotify_uri,
                Track.name,
                Track.normalized_title,
                Track.duration_ms,
                Track.explicit,
                Track.popularity,
                Track.preview_url,
                Track.external_url,
                SpotifyTrack.market_status,
                SpotifyTrack.is_playable,
                SpotifyTrack.last_seen_at,
                SpotifyTrack.album_id,
                LikedTrack.spotify_track_id,
                LikedTrack.added_at,
                LikedTrack.is_current,
                ExternalId.id_value,
            )
            .join(SpotifyTrack, SpotifyTrack.track_id == Track.id)
            .outerjoin(LikedTrack, LikedTrack.spotify_track_id == SpotifyTrack.spotify_track_id)
            .outerjoin(
                ExternalId,
                and_(ExternalId.track_id == Track.id, ExternalId.id_type == "isrc"),
            )
            .where(Track.id.in_(page_ids))
        )
        rows = session.execute(stmt).all()
        by_id = {r[0]: r for r in rows}
        result: list[TrackRow] = []
        for tid in page_ids:
            r = by_id.get(tid)
            if r is None:
                continue
            result.append(
                TrackRow(
                    track_id=r[0],
                    spotify_track_id=r[1],
                    spotify_uri=r[2],
                    title=r[3],
                    normalized_title=r[4],
                    duration_ms=r[5],
                    explicit=bool(r[6]),
                    popularity=r[7],
                    preview_url=r[8],
                    external_url=r[9],
                    market_status=r[10] or "unknown",
                    is_playable=r[11],
                    last_seen_at=r[12],
                    album_id=r[13],
                    liked=r[14] is not None,
                    liked_added_at=r[15],
                    is_current_liked=bool(r[16]) if r[14] is not None else False,
                    isrc=r[17],
                )
            )
        return result

    def fetch_artists_for_tracks(
        self, session: Session, track_ids: list[int]
    ) -> dict[int, list[dict[str, Any]]]:
        if not track_ids:
            return {}
        stmt = (
            select(
                TrackArtist.track_id,
                Artist.id,
                SpotifyArtist.spotify_artist_id,
                Artist.name,
                TrackArtist.position,
            )
            .join(Artist, TrackArtist.artist_id == Artist.id)
            .join(SpotifyArtist, SpotifyArtist.artist_id == Artist.id)
            .where(TrackArtist.track_id.in_(track_ids))
            .order_by(TrackArtist.track_id, TrackArtist.position)
        )
        out: dict[int, list[dict[str, Any]]] = {}
        for track_id, artist_id, sp_id, name, _pos in session.execute(stmt).all():
            out.setdefault(track_id, []).append(
                {
                    "artist_id": artist_id,
                    "spotify_artist_id": sp_id,
                    "name": name,
                }
            )
        return out

    def fetch_albums_for_tracks(
        self, session: Session, album_ids: list[int]
    ) -> dict[int, dict[str, Any]]:
        if not album_ids:
            return {}
        stmt = (
            select(
                Album.id,
                SpotifyAlbum.spotify_album_id,
                Album.name,
                Album.release_date,
            )
            .join(SpotifyAlbum, SpotifyAlbum.album_id == Album.id)
            .where(Album.id.in_(album_ids))
        )
        return {
            row[0]: {
                "album_id": row[0],
                "spotify_album_id": row[1],
                "name": row[2],
                "release_date": row[3],
            }
            for row in session.execute(stmt).all()
        }

    def fetch_playlist_counts_for_tracks(
        self, session: Session, spotify_track_ids: list[str]
    ) -> dict[str, int]:
        if not spotify_track_ids:
            return {}
        stmt = (
            select(
                PlaylistTrack.spotify_track_id,
                func.count(PlaylistTrack.id),
            )
            .where(
                PlaylistTrack.spotify_track_id.in_(spotify_track_ids),
                PlaylistTrack.is_current.is_(True),
            )
            .group_by(PlaylistTrack.spotify_track_id)
        )
        return dict(session.execute(stmt).all())

    def fetch_playlists_for_tracks(
        self, session: Session, spotify_track_ids: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        """Full playlist rows — used by dry-run / detail flows, not list search."""
        if not spotify_track_ids:
            return {}
        stmt = (
            select(
                PlaylistTrack.spotify_track_id,
                Playlist.id,
                Playlist.spotify_playlist_id,
                Playlist.name,
            )
            .join(Playlist, Playlist.spotify_playlist_id == PlaylistTrack.spotify_playlist_id)
            .where(
                PlaylistTrack.spotify_track_id.in_(spotify_track_ids),
                PlaylistTrack.is_current.is_(True),
            )
            .order_by(Playlist.name)
        )
        out: dict[str, list[dict[str, Any]]] = {}
        for sp_tid, pl_id, sp_pl_id, name in session.execute(stmt).all():
            out.setdefault(sp_tid, []).append(
                {
                    "playlist_id": pl_id,
                    "spotify_playlist_id": sp_pl_id,
                    "name": name,
                }
            )
        return out

    def duplicate_isrc_track_ids(self, session: Session) -> set[int]:
        dup_isrc = (
            select(ExternalId.id_value)
            .where(ExternalId.id_type == "isrc", ExternalId.id_value != "")
            .group_by(ExternalId.id_value)
            .having(func.count(ExternalId.track_id) > 1)
        )
        stmt = select(ExternalId.track_id).where(
            ExternalId.id_type == "isrc",
            ExternalId.id_value.in_(dup_isrc),
        )
        return set(session.execute(stmt).scalars().all())
