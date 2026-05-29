from __future__ import annotations

import secrets
import urllib.parse
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.settings.config import settings
from app.spotify.oauth_state import OAuthStateStore
from app.spotify.pkce import code_challenge_s256, generate_code_verifier
from app.spotify.schemas import AuthStartResponse, AuthStatusResponse, LogoutResponse
from app.spotify.token_store import SpotifyTokenStore

router = APIRouter(prefix="/spotify/auth")

_state_store = OAuthStateStore(ttl_seconds=600)
_token_store = SpotifyTokenStore()


def _scopes_list() -> list[str]:
    return [s for s in (settings.spotify_scopes or "").split(" ") if s]


@router.get("/start", response_model=AuthStartResponse)
def auth_start() -> AuthStartResponse:
    if not settings.spotify_client_id:
        raise HTTPException(
            status_code=400,
            detail="Spotify client is not configured (SPOTIFY_CLIENT_ID).",
        )

    state = secrets.token_urlsafe(24)
    code_verifier = generate_code_verifier()
    code_challenge = code_challenge_s256(code_verifier)
    _state_store.put(state, code_verifier)

    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "scope": " ".join(_scopes_list()),
    }
    authorize_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)
    return AuthStartResponse(authorize_url=authorize_url, state=state, expires_in_seconds=600)


@router.get("/callback", response_class=HTMLResponse)
async def auth_callback(
    request: Request, code: str | None = None, state: str | None = None
) -> HTMLResponse:
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state.")

    stored = _state_store.pop(state)
    if stored is None:
        raise HTTPException(status_code=400, detail="Invalid or expired state.")

    data = {
        "client_id": settings.spotify_client_id,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.spotify_redirect_uri,
        "code_verifier": stored.code_verifier,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://accounts.spotify.com/api/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail="Token exchange failed.")
        token_json = resp.json()

    # Phase 1: we store tokens for local dev only; user_id is resolved lazily.
    user_id = "me"
    _token_store.save_from_token_response(user_id=user_id, token_response=token_json)

    now = datetime.now(tz=UTC)
    html = f"""<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"/><title>Spotify Curator</title></head>
  <body>
    <h1>Authorization successful</h1>
    <p>You can close this window and return to the app.</p>
    <p><small>{now.isoformat()}</small></p>
  </body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


@router.get("/status", response_model=AuthStatusResponse)
def auth_status() -> AuthStatusResponse:
    tok = _token_store.load()
    if tok is None:
        return AuthStatusResponse(connected=False, scopes=[])
    expires_at = tok.expires_at.isoformat() if tok.expires_at else None
    scopes = [s for s in (tok.scope or "").split(" ") if s]
    return AuthStatusResponse(
        connected=True,
        scopes=scopes,
        token_expires_at=expires_at,
        user={"id": tok.user_id},
    )


@router.post("/logout", response_model=LogoutResponse)
def auth_logout() -> LogoutResponse:
    _token_store.clear()
    return LogoutResponse(ok=True)

