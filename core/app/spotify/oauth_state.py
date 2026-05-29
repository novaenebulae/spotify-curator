from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class OAuthState:
    code_verifier: str
    created_at_ms: int


class OAuthStateStore:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self._ttl_ms = ttl_seconds * 1000
        self._states: dict[str, OAuthState] = {}

    def put(self, state: str, code_verifier: str) -> None:
        now = int(time.time() * 1000)
        self._states[state] = OAuthState(code_verifier=code_verifier, created_at_ms=now)

    def pop(self, state: str) -> OAuthState | None:
        self._purge_expired()
        return self._states.pop(state, None)

    def _purge_expired(self) -> None:
        now = int(time.time() * 1000)
        expired = [k for k, v in self._states.items() if now - v.created_at_ms > self._ttl_ms]
        for k in expired:
            self._states.pop(k, None)

