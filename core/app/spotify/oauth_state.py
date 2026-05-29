from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_oauth import OAuthPkceState


@dataclass(frozen=True)
class OAuthState:
    code_verifier: str
    created_at_ms: int


class OAuthStateStore:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self._ttl_seconds = ttl_seconds

    def put(self, state: str, code_verifier: str) -> None:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        expires_at = now + timedelta(seconds=self._ttl_seconds)
        engine = get_engine()
        with Session(engine) as session:
            self._purge_expired(session, now)
            session.merge(
                OAuthPkceState(
                    state=state,
                    code_verifier=code_verifier,
                    expires_at=expires_at,
                    created_at=now,
                )
            )
            session.commit()

    def pop(self, state: str) -> OAuthState | None:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        engine = get_engine()
        with Session(engine) as session:
            self._purge_expired(session, now)
            row = session.get(OAuthPkceState, state)
            if row is None or row.expires_at < now:
                return None
            session.delete(row)
            session.commit()
            created_ms = int(row.created_at.timestamp() * 1000)
            return OAuthState(code_verifier=row.code_verifier, created_at_ms=created_ms)

    def _purge_expired(self, session: Session, now: datetime) -> None:
        session.execute(delete(OAuthPkceState).where(OAuthPkceState.expires_at < now))
