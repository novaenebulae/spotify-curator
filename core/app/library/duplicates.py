from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_library import (
    Album,
    Artist,
    ExternalId,
    SpotifyTrack,
    Track,
    TrackArtist,
)
from app.observability.errors import ApiError

DURATION_TOLERANCE_MS = 3000

STRATEGIES = frozenset(
    {"isrc", "spotify_track_id", "title_artist", "title_artist_duration", "all"}
)


@dataclass(frozen=True)
class DuplicateGroup:
    group_id: str
    strategy: str
    confidence: float
    reason: str
    tracks: list[dict[str, Any]]


class DuplicateDetectionService:
    def list_duplicates(
        self,
        *,
        strategy: str = "isrc",
        min_confidence: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        if strategy not in STRATEGIES:
            raise ApiError(
                code="VALIDATION_ERROR",
                message=f"Invalid strategy: {strategy}",
                status_code=400,
            )
        page = max(1, page)
        page_size = min(100, max(1, page_size))

        engine = get_engine()
        with Session(engine) as session:
            groups: list[DuplicateGroup] = []
            if strategy in ("isrc", "all"):
                groups.extend(self._groups_isrc(session))
            if strategy in ("spotify_track_id", "all"):
                groups.extend(self._groups_spotify_track_id(session))
            if strategy in ("title_artist", "all"):
                groups.extend(self._groups_title_artist(session, with_duration=False))
            if strategy in ("title_artist_duration", "all"):
                groups.extend(self._groups_title_artist(session, with_duration=True))

            if strategy == "all":
                groups = self._dedupe_groups(groups)

            groups = [g for g in groups if g.confidence >= min_confidence]
            groups.sort(key=lambda g: (-g.confidence, g.group_id))

            total_groups = len(groups)
            offset = (page - 1) * page_size
            page_groups = groups[offset : offset + page_size]

            by_strategy: dict[str, int] = {}
            track_count = 0
            for g in groups:
                by_strategy[g.strategy] = by_strategy.get(g.strategy, 0) + 1
                track_count += len(g.tracks)

        total_pages = math.ceil(total_groups / page_size) if total_groups else 0
        return {
            "groups": [
                {
                    "group_id": g.group_id,
                    "strategy": g.strategy,
                    "confidence": g.confidence,
                    "reason": g.reason,
                    "tracks": g.tracks,
                }
                for g in page_groups
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_groups": total_groups,
                "total_pages": total_pages,
            },
            "summary": {
                "group_count": total_groups,
                "track_count": track_count,
                "by_strategy": by_strategy,
            },
        }

    def _track_summary(self, session: Session, track_ids: list[int]) -> list[dict[str, Any]]:
        if not track_ids:
            return []
        stmt = (
            select(
                Track.id,
                SpotifyTrack.spotify_track_id,
                Track.name,
                Track.duration_ms,
                ExternalId.id_value,
                Album.name,
            )
            .join(SpotifyTrack, SpotifyTrack.track_id == Track.id)
            .outerjoin(
                ExternalId,
                and_(ExternalId.track_id == Track.id, ExternalId.id_type == "isrc"),
            )
            .outerjoin(Album, Album.id == SpotifyTrack.album_id)
            .where(Track.id.in_(track_ids))
        )
        rows = session.execute(stmt).all()
        artist_map = self._primary_artists(session, track_ids)
        out = []
        for tid, sp_id, title, dur, isrc, album_name in rows:
            out.append(
                {
                    "track_id": tid,
                    "spotify_track_id": sp_id,
                    "title": title,
                    "artist_names": artist_map.get(tid, []),
                    "album_name": album_name,
                    "duration_ms": dur,
                    "isrc": isrc,
                }
            )
        return out

    def _primary_artists(self, session: Session, track_ids: list[int]) -> dict[int, list[str]]:
        stmt = (
            select(TrackArtist.track_id, Artist.name)
            .join(Artist, TrackArtist.artist_id == Artist.id)
            .where(TrackArtist.track_id.in_(track_ids), TrackArtist.position == 0)
        )
        out: dict[int, list[str]] = {}
        for tid, name in session.execute(stmt).all():
            out.setdefault(tid, []).append(name)
        return out

    def _groups_isrc(self, session: Session) -> list[DuplicateGroup]:
        dup_values = (
            select(ExternalId.id_value)
            .where(ExternalId.id_type == "isrc", ExternalId.id_value != "")
            .group_by(ExternalId.id_value)
            .having(func.count(ExternalId.track_id) > 1)
        )
        groups: list[DuplicateGroup] = []
        for isrc in session.execute(dup_values).scalars().all():
            track_ids = list(
                session.execute(
                    select(ExternalId.track_id).where(
                        ExternalId.id_type == "isrc", ExternalId.id_value == isrc
                    )
                )
                .scalars()
                .all()
            )
            if len(track_ids) < 2:
                continue
            groups.append(
                DuplicateGroup(
                    group_id=f"dup_isrc_{isrc}",
                    strategy="isrc",
                    confidence=1.0,
                    reason="same_isrc",
                    tracks=self._track_summary(session, track_ids),
                )
            )
        return groups

    def _groups_spotify_track_id(self, session: Session) -> list[DuplicateGroup]:
        # 1:1 spotify_track_id in schema; flag tracks appearing in multiple playlist contexts
        # is handled elsewhere — no duplicate spotify_track_id rows expected.
        return []

    def _groups_title_artist(
        self, session: Session, *, with_duration: bool
    ) -> list[DuplicateGroup]:
        stmt = (
            select(
                Track.id,
                Track.normalized_title,
                Track.duration_ms,
                Artist.normalized_name,
            )
            .join(TrackArtist, TrackArtist.track_id == Track.id)
            .join(Artist, TrackArtist.artist_id == Artist.id)
            .where(TrackArtist.position == 0)
        )
        buckets: dict[str, list[int]] = {}
        meta: dict[int, tuple[str, int, str]] = {}
        for tid, norm_title, dur, norm_artist in session.execute(stmt).all():
            if with_duration:
                bucket = f"{norm_title}|{norm_artist}|{dur // DURATION_TOLERANCE_MS}"
            else:
                bucket = f"{norm_title}|{norm_artist}"
            buckets.setdefault(bucket, []).append(tid)
            meta[tid] = (norm_title, dur, norm_artist)

        groups: list[DuplicateGroup] = []
        for key, track_ids in buckets.items():
            if len(track_ids) < 2:
                continue
            if with_duration:
                durs = [meta[tid][1] for tid in track_ids]
                if max(durs) - min(durs) > DURATION_TOLERANCE_MS:
                    continue
                confidence = 0.85
                reason = "same_title_artist_similar_duration"
                strategy = "title_artist_duration"
                group_id = f"dup_title_artist_dur_{key}"
            else:
                confidence = 0.85
                reason = "same_title_primary_artist"
                strategy = "title_artist"
                group_id = f"dup_title_artist_{key}"
            groups.append(
                DuplicateGroup(
                    group_id=group_id,
                    strategy=strategy,
                    confidence=confidence,
                    reason=reason,
                    tracks=self._track_summary(session, track_ids),
                )
            )
        return groups

    def _dedupe_groups(self, groups: list[DuplicateGroup]) -> list[DuplicateGroup]:
        seen_track_sets: set[frozenset[int]] = set()
        unique: list[DuplicateGroup] = []
        for g in groups:
            key = frozenset(t["track_id"] for t in g.tracks)
            if key in seen_track_sets:
                continue
            seen_track_sets.add(key)
            unique.append(g)
        return unique
