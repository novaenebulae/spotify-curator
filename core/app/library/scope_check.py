from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_spotify_auth import SpotifyAuthToken

WRITE_SCOPES_BY_ACTION: dict[str, frozenset[str]] = {
    "unlike_tracks": frozenset({"user-library-modify"}),
    "restore_liked_tracks": frozenset({"user-library-modify"}),
    "create_backup_playlist": frozenset(
        {"playlist-modify-private", "playlist-modify-public"}
    ),
}


def get_current_scopes() -> list[str]:
    engine = get_engine()
    with Session(engine) as session:
        row = session.execute(select(SpotifyAuthToken).limit(1)).scalar_one_or_none()
        if row is None or not row.scope:
            return []
        return [s for s in row.scope.split(" ") if s]


def check_write_scopes(action_type: str) -> tuple[bool, list[dict[str, Any]]]:
    required = WRITE_SCOPES_BY_ACTION.get(action_type, frozenset())
    if not required:
        return True, []

    scopes = set(get_current_scopes())
    if action_type == "create_backup_playlist":
        has_scope = bool(scopes & required)
    else:
        has_scope = required.issubset(scopes)

    if has_scope:
        return True, []

    return False, [
        {
            "code": "WRITE_SCOPE_MISSING",
            "message": "Spotify write scope is not available.",
        }
    ]
