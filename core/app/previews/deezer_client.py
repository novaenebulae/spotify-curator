from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.previews.schemas import DeezerTrackResult
from app.settings.config import settings

_logger = logging.getLogger(__name__)


class DeezerClientError(Exception):
    pass


class DeezerHTTPError(DeezerClientError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


class DeezerClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base = (base_url or settings.deezer_api_base_url).rstrip("/")
        self._timeout = timeout_seconds if timeout_seconds is not None else settings.deezer_timeout_seconds
        self._max_retries = max_retries if max_retries is not None else settings.deezer_max_retries
        self._transport = transport

    def search_track(self, query: str, *, limit: int = 10) -> list[DeezerTrackResult]:
        url = f"{self._base}/search/track"
        data = self._get_json(url, params={"q": query, "limit": limit})
        items = data.get("data") or []
        return [self._parse_track(item) for item in items if isinstance(item, dict)]

    def get_track(self, deezer_id: str) -> DeezerTrackResult:
        url = f"{self._base}/track/{deezer_id}"
        data = self._get_json(url)
        return self._parse_track(data)

    def _get_json(self, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        last_err: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                    resp = client.get(url, params=params)
                if resp.status_code == 429:
                    if attempt < self._max_retries:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    raise DeezerHTTPError(429, "Deezer rate limited")
                if resp.status_code >= 400:
                    raise DeezerHTTPError(resp.status_code, resp.text[:500])
                body = resp.json()
                if isinstance(body, dict) and body.get("error"):
                    err = body["error"]
                    msg = err.get("message", "Deezer API error") if isinstance(err, dict) else str(err)
                    raise DeezerClientError(msg)
                if not isinstance(body, dict):
                    raise DeezerClientError("Invalid Deezer response")
                return body
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_err = exc
                if attempt < self._max_retries:
                    time.sleep(0.3 * (attempt + 1))
                    continue
                raise DeezerClientError(str(exc)) from exc
        raise DeezerClientError(str(last_err or "unknown"))

    @staticmethod
    def _parse_track(item: dict[str, Any]) -> DeezerTrackResult:
        artist = item.get("artist") or {}
        album = item.get("album") or {}
        artist_name = artist.get("name", "") if isinstance(artist, dict) else str(artist)
        album_title = album.get("title") if isinstance(album, dict) else None
        return DeezerTrackResult(
            id=str(item.get("id", "")),
            title=str(item.get("title", "")),
            artist_name=artist_name,
            album_title=str(album_title) if album_title else None,
            preview_url=item.get("preview") or None,
            duration_seconds=float(item["duration"]) if item.get("duration") is not None else None,
            link=item.get("link"),
            isrc=item.get("isrc"),
        )
