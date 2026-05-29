from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.settings.config import settings
from app.spotify.token_store import SpotifyTokenStore

DEFAULT_SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
DEFAULT_SPOTIFY_ACCOUNTS_BASE_URL = "https://accounts.spotify.com"


class SpotifyError(RuntimeError):
    pass


class SpotifyAuthError(SpotifyError):
    pass


class SpotifyRateLimited(SpotifyError):
    def __init__(self, retry_after_seconds: int | None) -> None:
        super().__init__("Spotify rate limited")
        self.retry_after_seconds = retry_after_seconds


class SpotifyHTTPError(SpotifyError):
    def __init__(self, status_code: int, body: str | None = None) -> None:
        super().__init__(f"Spotify HTTP {status_code}")
        self.status_code = status_code
        self.body = body


@dataclass(frozen=True)
class SpotifyResponsePage:
    items: list[dict[str, Any]]
    next_url: str | None
    total: int | None


class SpotifyClient:
    def __init__(
        self,
        token_store: SpotifyTokenStore | None = None,
        *,
        api_base_url: str = DEFAULT_SPOTIFY_API_BASE_URL,
        accounts_base_url: str = DEFAULT_SPOTIFY_ACCOUNTS_BASE_URL,
        transport: httpx.BaseTransport | None = None,
        sleeper: callable | None = None,
    ) -> None:
        self._token_store = token_store or SpotifyTokenStore()
        self._api_base_url = api_base_url.rstrip("/")
        self._accounts_base_url = accounts_base_url.rstrip("/")
        self._transport = transport
        self._sleep = sleeper or time.sleep

    def _get_access_token(self) -> str:
        tok = self._token_store.load()
        if tok is None:
            raise SpotifyAuthError("Not authenticated.")
        return tok.access_token

    def _get_refresh_token(self) -> str | None:
        tok = self._token_store.load()
        if tok is None:
            return None
        return tok.refresh_token

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=30, transport=self._transport)

    def _parse_retry_after(self, resp: httpx.Response) -> int | None:
        ra = resp.headers.get("Retry-After")
        if ra and ra.isdigit():
            return int(ra)
        return None

    def _refresh_access_token(self) -> None:
        refresh_token = self._get_refresh_token()
        if not refresh_token:
            raise SpotifyAuthError("Missing refresh token.")

        data = {
            "client_id": settings.spotify_client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        with self._client() as client:
            resp = client.post(
                f"{self._accounts_base_url}/api/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code >= 400:
            raise SpotifyAuthError("Token refresh failed.")
        token_json = resp.json()
        # Phase 1 token storage is local dev only; user_id is kept stable.
        self._token_store.save_from_token_response(user_id="me", token_response=token_json)

    def _request_json(self, method: str, url: str, *, params: dict | None = None) -> dict:
        max_attempts = 5
        refreshed = False

        for attempt in range(max_attempts):
            headers = {"Authorization": f"Bearer {self._get_access_token()}"}
            with self._client() as client:
                resp = client.request(method, url, params=params, headers=headers)

            if resp.status_code == 401 and not refreshed:
                self._refresh_access_token()
                refreshed = True
                continue

            if resp.status_code == 429:
                retry_after = self._parse_retry_after(resp)
                # Respect Retry-After when provided.
                if retry_after is not None:
                    self._sleep(retry_after)
                else:
                    # Minimal exponential backoff: 1,2,4,8...
                    self._sleep(min(2**attempt, 30))
                continue

            if 500 <= resp.status_code < 600:
                self._sleep(min(2**attempt, 30))
                continue

            if resp.status_code >= 400:
                body = None
                try:
                    body = json.dumps(resp.json())
                except Exception:
                    body = resp.text
                raise SpotifyHTTPError(resp.status_code, body=body)

            return resp.json()

        raise SpotifyError("Spotify request failed after retries.")

    def get_current_user(self) -> dict:
        return self._request_json("GET", f"{self._api_base_url}/me")

    def get_saved_tracks_page(self, *, limit: int = 50, offset: int = 0) -> SpotifyResponsePage:
        payload = self._request_json(
            "GET",
            f"{self._api_base_url}/me/tracks",
            params={"limit": limit, "offset": offset},
        )
        return SpotifyResponsePage(
            items=payload.get("items", []),
            next_url=payload.get("next"),
            total=payload.get("total"),
        )

    def get_playlists_page(self, *, limit: int = 50, offset: int = 0) -> SpotifyResponsePage:
        payload = self._request_json(
            "GET",
            f"{self._api_base_url}/me/playlists",
            params={"limit": limit, "offset": offset},
        )
        return SpotifyResponsePage(
            items=payload.get("items", []),
            next_url=payload.get("next"),
            total=payload.get("total"),
        )

    def get_playlist_items_page(
        self, *, playlist_id: str, limit: int = 100, offset: int = 0
    ) -> SpotifyResponsePage:
        payload = self._request_json(
            "GET",
            f"{self._api_base_url}/playlists/{playlist_id}/tracks",
            params={"limit": limit, "offset": offset},
        )
        return SpotifyResponsePage(
            items=payload.get("items", []),
            next_url=payload.get("next"),
            total=payload.get("total"),
        )

    def iter_saved_tracks(self, *, limit: int = 50) -> list[dict]:
        offset = 0
        out: list[dict] = []
        while True:
            page = self.get_saved_tracks_page(limit=limit, offset=offset)
            out.extend(page.items)
            if not page.next_url:
                break
            offset += limit
        return out

    def iter_playlists(self, *, limit: int = 50) -> list[dict]:
        offset = 0
        out: list[dict] = []
        while True:
            page = self.get_playlists_page(limit=limit, offset=offset)
            out.extend(page.items)
            if not page.next_url:
                break
            offset += limit
        return out

    def iter_playlist_items(self, *, playlist_id: str, limit: int = 100) -> list[dict]:
        offset = 0
        out: list[dict] = []
        while True:
            page = self.get_playlist_items_page(playlist_id=playlist_id, limit=limit, offset=offset)
            out.extend(page.items)
            if not page.next_url:
                break
            offset += limit
        return out

