from __future__ import annotations

from pydantic import BaseModel


class AuthStartResponse(BaseModel):
    authorize_url: str
    state: str
    expires_in_seconds: int


class AuthStatusResponse(BaseModel):
    connected: bool
    scopes: list[str]
    token_expires_at: str | None = None
    user: dict | None = None


class LogoutResponse(BaseModel):
    ok: bool = True

