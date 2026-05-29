from __future__ import annotations

from pydantic import BaseModel, computed_field, model_validator


class AuthStartResponse(BaseModel):
    authorize_url: str
    authorization_url: str = ""
    state: str
    expires_in_seconds: int

    @model_validator(mode="after")
    def _sync_authorization_url(self) -> AuthStartResponse:
        if not self.authorization_url:
            self.authorization_url = self.authorize_url
        return self


class AuthStatusResponse(BaseModel):
    connected: bool
    scopes: list[str]
    token_expires_at: str | None = None
    user: dict | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def authenticated(self) -> bool:
        return self.connected


class LogoutResponse(BaseModel):
    ok: bool = True
