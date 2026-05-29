from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_spotify_auth import SpotifyAuthToken


@dataclass(frozen=True)
class StoredToken:
    user_id: str
    access_token: str
    refresh_token: str | None
    token_type: str
    scope: str
    expires_at: datetime | None
    raw: dict


class SpotifyTokenStore:
    def load(self) -> StoredToken | None:
        engine = get_engine()
        with Session(engine) as session:
            row = session.execute(select(SpotifyAuthToken).limit(1)).scalar_one_or_none()
            if row is None:
                return None
            raw = json.loads(row.raw_json or "{}")
            return StoredToken(
                user_id=row.user_id,
                access_token=row.access_token,
                refresh_token=row.refresh_token,
                token_type=row.token_type,
                scope=row.scope,
                expires_at=row.expires_at,
                raw=raw,
            )

    def save_from_token_response(self, *, user_id: str, token_response: dict) -> StoredToken:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        expires_in = int(token_response.get("expires_in") or 0) or None
        expires_at = (now + timedelta(seconds=expires_in)) if expires_in else None

        scope = token_response.get("scope") or ""
        access_token = token_response["access_token"]
        refresh_token = token_response.get("refresh_token")
        token_type = token_response.get("token_type") or "Bearer"

        engine = get_engine()
        with Session(engine) as session:
            existing = session.get(SpotifyAuthToken, user_id)
            raw_json = json.dumps(token_response)
            if existing is None:
                obj = SpotifyAuthToken(
                    user_id=user_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type=token_type,
                    scope=scope,
                    expires_at=expires_at,
                    raw_json=raw_json,
                    created_at=now,
                    updated_at=now,
                )
                session.add(obj)
            else:
                existing.access_token = access_token
                existing.refresh_token = refresh_token or existing.refresh_token
                existing.token_type = token_type
                existing.scope = scope
                existing.expires_at = expires_at
                existing.raw_json = raw_json
                existing.updated_at = now
            session.commit()

        return StoredToken(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            scope=scope,
            expires_at=expires_at,
            raw=token_response,
        )

    def clear(self) -> None:
        engine = get_engine()
        with Session(engine) as session:
            session.execute(delete(SpotifyAuthToken))
            session.commit()

