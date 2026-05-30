from __future__ import annotations

import json
import math
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_library import LikedTrack, SpotifyTrack, Track
from app.database.repositories.library_actions import LibraryActionsRepository
from app.library.scope_check import WRITE_SCOPES_BY_ACTION, check_write_scopes
from app.library.search import TrackSearchService
from app.observability.errors import ApiError

MAX_AFFECTED_TRACKS = 500
VALID_ACTION_TYPES = frozenset(
    {"unlike_tracks", "restore_liked_tracks", "create_backup_playlist"}
)
PLAYLIST_NAME_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,100}$")


class LibraryActionsService:
    def __init__(self) -> None:
        self._repo = LibraryActionsRepository()
        self._search = TrackSearchService()

    def dry_run(
        self,
        *,
        action_type: str,
        track_ids: list[int] | None = None,
        filter: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if action_type not in VALID_ACTION_TYPES:
            raise ApiError(
                code="VALIDATION_ERROR",
                message=f"Invalid action_type: {action_type}",
                status_code=400,
            )

        options = options or {}
        filter = filter or {}
        track_ids = track_ids or []

        if not track_ids and not filter:
            raise ApiError(
                code="VALIDATION_ERROR",
                message="track_ids or filter is required.",
                status_code=400,
            )

        resolved_ids = track_ids
        if not resolved_ids and filter:
            resolved_ids = self._search.search_track_ids(filter, limit=MAX_AFFECTED_TRACKS + 1)

        if len(resolved_ids) > MAX_AFFECTED_TRACKS:
            raise ApiError(
                code="VALIDATION_ERROR",
                message=f"Action affects more than {MAX_AFFECTED_TRACKS} tracks.",
                status_code=400,
                details={"affected_count": len(resolved_ids), "max": MAX_AFFECTED_TRACKS},
            )

        has_scope, scope_warnings = check_write_scopes(action_type)
        warnings: list[dict[str, Any]] = list(scope_warnings)
        blocked = False

        if action_type == "create_backup_playlist":
            name = options.get("backup_playlist_name") or ""
            if not name or not PLAYLIST_NAME_RE.match(name):
                raise ApiError(
                    code="VALIDATION_ERROR",
                    message="Invalid backup_playlist_name.",
                    status_code=400,
                )

        affected_tracks, action_warnings = self._build_affected(action_type, resolved_ids)
        warnings.extend(action_warnings)

        result: dict[str, Any] = {
            "affected_tracks": affected_tracks,
            "options": options,
        }
        if action_type == "create_backup_playlist":
            result["proposed_playlist"] = {
                "name": options.get("backup_playlist_name"),
                "track_uris": [
                    t.get("spotify_uri") for t in affected_tracks if t.get("spotify_uri")
                ],
            }

        engine = get_engine()
        with Session(engine) as session:
            row = self._repo.create(
                session,
                action_type=action_type,
                filter_json=filter,
                selected_track_ids=track_ids,
                affected_count=len(affected_tracks),
                dry_run=True,
                result=result,
                warnings=warnings,
            )
            action_id = row.id

        return {
            "action_id": action_id,
            "dry_run": True,
            "action_type": action_type,
            "affected_count": len(affected_tracks),
            "affected_tracks": affected_tracks,
            "warnings": warnings,
            "blocked": blocked,
            "requires_write_scope": action_type in WRITE_SCOPES_BY_ACTION,
            "spotify_applied": False,
        }

    def _build_affected(
        self, action_type: str, track_ids: list[int]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not track_ids:
            return [], []

        engine = get_engine()
        warnings: list[dict[str, Any]] = []
        with Session(engine) as session:
            stmt = (
                select(
                    Track.id,
                    Track.name,
                    SpotifyTrack.spotify_track_id,
                    SpotifyTrack.spotify_uri,
                    LikedTrack.spotify_track_id,
                    LikedTrack.is_current,
                )
                .join(SpotifyTrack, SpotifyTrack.track_id == Track.id)
                .outerjoin(LikedTrack, LikedTrack.spotify_track_id == SpotifyTrack.spotify_track_id)
                .where(Track.id.in_(track_ids))
            )
            rows = session.execute(stmt).all()
            found = {r[0] for r in rows}
            missing = set(track_ids) - found
            if missing:
                warnings.append(
                    {
                        "code": "TRACKS_NOT_FOUND",
                        "message": f"{len(missing)} track(s) not found.",
                        "details": {"track_ids": sorted(missing)},
                    }
                )

            affected: list[dict[str, Any]] = []
            for tid, title, sp_id, uri, liked_sp, is_current in rows:
                artist_names = self._artist_names(session, tid)
                reason = "selected"
                if action_type == "unlike_tracks":
                    if liked_sp is None or not is_current:
                        warnings.append(
                            {
                                "code": "NOT_CURRENTLY_LIKED",
                                "message": f"Track {tid} is not a current liked track.",
                            }
                        )
                        continue
                elif action_type == "restore_liked_tracks":
                    if liked_sp is not None and is_current:
                        warnings.append(
                            {
                                "code": "ALREADY_LIKED",
                                "message": f"Track {tid} is already in current likes.",
                            }
                        )
                        continue
                    if not sp_id:
                        warnings.append(
                            {
                                "code": "NOT_RESTORABLE",
                                "message": f"Track {tid} has no spotify_track_id.",
                            }
                        )
                        continue
                affected.append(
                    {
                        "track_id": tid,
                        "spotify_track_id": sp_id,
                        "spotify_uri": uri,
                        "title": title,
                        "artist_names": artist_names,
                        "reason": reason,
                    }
                )
        return affected, warnings

    def _artist_names(self, session: Session, track_id: int) -> list[str]:
        from app.database.models_library import Artist, TrackArtist

        stmt = (
            select(Artist.name)
            .join(TrackArtist, TrackArtist.artist_id == Artist.id)
            .where(TrackArtist.track_id == track_id)
            .order_by(TrackArtist.position)
        )
        return list(session.execute(stmt).scalars().all())

    def list_actions(
        self,
        *,
        action_type: str | None = None,
        dry_run: bool | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        engine = get_engine()
        with Session(engine) as session:
            rows, total = self._repo.list_actions(
                session,
                action_type=action_type,
                dry_run=dry_run,
                status=status,
                page=page,
                page_size=page_size,
            )
            items = [self._serialize_action(r) for r in rows]

        total_pages = math.ceil(total / page_size) if total else 0
        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        }

    def get_action(self, action_id: int) -> dict[str, Any]:
        engine = get_engine()
        with Session(engine) as session:
            row = self._repo.get_by_id(session, action_id)
            if row is None:
                raise ApiError(code="NOT_FOUND", message="Action not found.", status_code=404)
            return self._serialize_action(row, detailed=True)

    def _serialize_action(self, row, *, detailed: bool = False) -> dict[str, Any]:
        base = {
            "id": row.id,
            "action_type": row.action_type,
            "dry_run": row.dry_run,
            "spotify_applied": row.spotify_applied,
            "status": row.status,
            "affected_count": row.affected_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
        if not detailed:
            return base
        return {
            **base,
            "filter": json.loads(row.filter_json or "{}"),
            "selected_track_ids": json.loads(row.selected_track_ids_json or "[]"),
            "result": json.loads(row.result_json or "{}"),
            "warnings": json.loads(row.warning_json or "[]"),
        }
