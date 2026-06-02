from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.reccobeats.errors import (
    ReccoBeatsError,
    ReccoBeatsHTTPError,
    ReccoBeatsNotFound,
    ReccoBeatsRateLimited,
    ReccoBeatsTimeout,
)
from app.reccobeats.parsing import extract_batch_item_dicts, map_requested_ids_to_raw_items
from app.reccobeats.schemas import (
    ReccoBeatsArtist,
    ReccoBeatsAudioFeatures,
    ReccoBeatsBatchEntry,
    ReccoBeatsBatchResult,
    ReccoBeatsFetchResult,
    ReccoBeatsTrackMeta,
)
from app.settings.config import settings

DEFAULT_RECCOBEATS_BASE_URL = "https://api.reccobeats.com"
_logger = logging.getLogger(__name__)

_SPOTIFY_TRACK_RE = re.compile(r"open\.spotify\.com/track/([^/?#]+)")


class ReccoBeatsEndpoints:
    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")

    def tracks_by_ids(self, ids: list[str]) -> str:
        return f"{self._base}/v1/track"

    def track_audio_features(self, reccobeats_track_id: str) -> str:
        return f"{self._base}/v1/track/{reccobeats_track_id}/audio-features"

    def audio_features_batch(self) -> str:
        return f"{self._base}/v1/audio-features"


class ReccoBeatsClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        transport: httpx.BaseTransport | None = None,
        sleeper: callable | None = None,
    ) -> None:
        self._base_url = (base_url or settings.reccobeats_base_url).rstrip("/")
        self._timeout = (
            timeout_seconds if timeout_seconds is not None else settings.reccobeats_timeout_seconds
        )
        self._max_retries = (
            max_retries if max_retries is not None else settings.reccobeats_max_retries
        )
        self._transport = transport
        self._sleep = sleeper or time.sleep
        self._endpoints = ReccoBeatsEndpoints(self._base_url)

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self._timeout, transport=self._transport)

    def _parse_retry_after(self, resp: httpx.Response) -> int | None:
        ra = resp.headers.get("Retry-After")
        if ra and ra.isdigit():
            return int(ra)
        return None

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with self._client() as client:
                    resp = client.request(method, url, params=params)
            except httpx.TimeoutException as exc:
                last_error = ReccoBeatsTimeout()
                if attempt >= self._max_retries:
                    raise last_error from exc
                self._sleep(min(2**attempt, 30))
                continue
            except httpx.HTTPError as exc:
                last_error = ReccoBeatsError(
                    str(exc), code="RECCOBEATS_NETWORK_ERROR", retryable=True
                )
                if attempt >= self._max_retries:
                    raise last_error from exc
                self._sleep(min(2**attempt, 30))
                continue

            if resp.status_code == 429:
                retry_after = self._parse_retry_after(resp)
                if attempt >= self._max_retries:
                    raise ReccoBeatsRateLimited(retry_after)
                if retry_after is not None:
                    self._sleep(retry_after)
                else:
                    self._sleep(min(2**attempt, 30))
                continue

            if 500 <= resp.status_code < 600:
                if attempt >= self._max_retries:
                    body = resp.text
                    raise ReccoBeatsHTTPError(resp.status_code, body=body)
                self._sleep(min(2**attempt, 30))
                continue

            path = urlparse(url).path
            ids_param = (params or {}).get("ids", "")
            id_count = len([p for p in str(ids_param).split(",") if p.strip()]) if ids_param else 0
            if path.endswith("/audio-features") and "ids" in (params or {}):
                _logger.info(
                    "ReccoBeats batch HTTP %s %s ids_count=%s status=%s",
                    method,
                    path,
                    id_count,
                    resp.status_code,
                )

            return resp

        if last_error is not None:
            raise last_error
        raise ReccoBeatsError("ReccoBeats request failed after retries")

    def _extract_spotify_id_from_href(self, href: str | None) -> str | None:
        if not href:
            return None
        match = _SPOTIFY_TRACK_RE.search(href)
        if match:
            return match.group(1)
        parsed = urlparse(href)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[-2] == "track":
            return parts[-1]
        return None

    def _parse_track_meta(
        self, raw: dict[str, Any], *, fallback_spotify_id: str | None = None
    ) -> ReccoBeatsTrackMeta:
        artists_raw = raw.get("artists") or []
        artists = [
            ReccoBeatsArtist(
                id=str(a.get("id", "")),
                name=str(a.get("name", "")),
                href=a.get("href"),
            )
            for a in artists_raw
            if isinstance(a, dict)
        ]
        href = raw.get("href")
        spotify_id = fallback_spotify_id or self._extract_spotify_id_from_href(href)
        return ReccoBeatsTrackMeta(
            id=str(raw.get("id", "")),
            track_title=str(raw.get("trackTitle") or raw.get("track_title") or ""),
            artists=artists,
            duration_ms=raw.get("durationMs") or raw.get("duration_ms"),
            isrc=raw.get("isrc"),
            href=href,
            spotify_track_id=spotify_id,
        )

    def _parse_audio_features(self, raw: dict[str, Any]) -> ReccoBeatsAudioFeatures:
        return ReccoBeatsAudioFeatures(
            acousticness=_as_float(raw.get("acousticness")),
            danceability=_as_float(raw.get("danceability")),
            energy=_as_float(raw.get("energy")),
            instrumentalness=_as_float(raw.get("instrumentalness")),
            key=_as_int(raw.get("key")),
            liveness=_as_float(raw.get("liveness")),
            loudness=_as_float(raw.get("loudness")),
            mode=_as_int(raw.get("mode")),
            speechiness=_as_float(raw.get("speechiness")),
            tempo=_as_float(raw.get("tempo")),
            valence=_as_float(raw.get("valence")),
            time_signature=_as_int(raw.get("timeSignature") or raw.get("time_signature")),
            duration_ms=_as_int(raw.get("durationMs") or raw.get("duration_ms")),
        )

    def get_track_by_spotify_id(self, spotify_track_id: str) -> ReccoBeatsTrackMeta | None:
        resp = self._request(
            "GET",
            self._endpoints.tracks_by_ids([spotify_track_id]),
            params={"ids": spotify_track_id},
        )
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            body = resp.text
            if resp.status_code == 404:
                raise ReccoBeatsNotFound(body)
            raise ReccoBeatsHTTPError(resp.status_code, body=body)

        payload = _safe_json(resp)
        if not payload:
            return None

        tracks = _extract_track_list(payload)
        if not tracks:
            return None

        raw = tracks[0]
        if not raw.get("id"):
            return None
        return self._parse_track_meta(raw, fallback_spotify_id=spotify_track_id)

    def get_audio_features_batch(self, ids: list[str]) -> ReccoBeatsBatchResult:
        max_size = max(1, min(40, int(settings.reccobeats_http_batch_size)))
        if not ids:
            raise ReccoBeatsError(
                "At least one id is required for batch audio features",
                code="RECCOBEATS_BATCH_EMPTY",
                retryable=False,
            )
        if len(ids) > max_size:
            raise ReccoBeatsError(
                f"Batch size {len(ids)} exceeds maximum {max_size}",
                code="RECCOBEATS_BATCH_TOO_LARGE",
                retryable=False,
            )

        resp = self._request(
            "GET",
            self._endpoints.audio_features_batch(),
            params={"ids": ",".join(ids)},
        )
        if resp.status_code == 404:
            return ReccoBeatsBatchResult(entries=[], raw_payload={}, status_code=404)
        if resp.status_code >= 400:
            raise ReccoBeatsHTTPError(resp.status_code, body=resp.text)

        payload = _safe_json(resp)
        if payload is None and resp.content:
            try:
                parsed = resp.json()
                if isinstance(parsed, list):
                    payload = {"content": parsed}
            except json.JSONDecodeError:
                payload = None

        raw_payload: dict[str, Any] = payload if isinstance(payload, dict) else {"items": payload}
        raw_items = extract_batch_item_dicts(payload)
        id_to_raw = map_requested_ids_to_raw_items(raw_items, ids)

        entries: list[ReccoBeatsBatchEntry] = []
        for request_id in ids:
            raw = id_to_raw.get(request_id)
            if raw is None:
                entries.append(
                    ReccoBeatsBatchEntry(
                        request_id=request_id,
                        features=None,
                        track=None,
                        raw={},
                        features_status_code=resp.status_code,
                    )
                )
                continue

            track_meta: ReccoBeatsTrackMeta | None = None
            if raw.get("id") or raw.get("trackTitle") or raw.get("track_title"):
                track_meta = self._parse_track_meta(raw, fallback_spotify_id=request_id)
            features = self._parse_audio_features(raw)
            nested = raw.get("audioFeatures")
            if isinstance(nested, dict) and not _features_has_values(features):
                features = self._parse_audio_features(nested)
            entries.append(
                ReccoBeatsBatchEntry(
                    request_id=request_id,
                    features=features,
                    track=track_meta,
                    raw=raw,
                    features_status_code=resp.status_code,
                )
            )

        return ReccoBeatsBatchResult(
            entries=entries,
            raw_payload=raw_payload,
            status_code=resp.status_code,
        )

    def get_audio_features(
        self, reccobeats_track_id: str
    ) -> tuple[ReccoBeatsAudioFeatures | None, dict[str, Any], int]:
        resp = self._request("GET", self._endpoints.track_audio_features(reccobeats_track_id))
        if resp.status_code == 404:
            raise ReccoBeatsNotFound()
        if resp.status_code >= 400:
            raise ReccoBeatsHTTPError(resp.status_code, body=resp.text)

        payload = _safe_json(resp)
        if not payload:
            return None, {}, resp.status_code
        features = self._parse_audio_features(payload)
        return features, payload, resp.status_code

    def fetch_track_features(
        self,
        *,
        spotify_track_id: str | None = None,
        reccobeats_track_id: str | None = None,
    ) -> ReccoBeatsFetchResult:
        """Deprecated: use get_audio_features_batch. Kept for unit tests only."""
        track_meta: ReccoBeatsTrackMeta | None = None
        track_raw: dict[str, Any] = {}
        track_status: int | None = None

        rb_id = reccobeats_track_id
        if rb_id is None and spotify_track_id:
            resp = self._request(
                "GET",
                self._endpoints.tracks_by_ids([spotify_track_id]),
                params={"ids": spotify_track_id},
            )
            track_status = resp.status_code
            if resp.status_code == 404:
                return ReccoBeatsFetchResult(
                    track=None,
                    features=None,
                    track_status_code=404,
                )
            if resp.status_code >= 400:
                raise ReccoBeatsHTTPError(resp.status_code, body=resp.text)

            payload = _safe_json(resp)
            track_raw = payload if isinstance(payload, dict) else {}
            tracks = _extract_track_list(payload) if payload else []
            if not tracks or not tracks[0].get("id"):
                return ReccoBeatsFetchResult(
                    track=None,
                    features=None,
                    track_raw=track_raw,
                    track_status_code=track_status,
                )
            track_meta = self._parse_track_meta(tracks[0], fallback_spotify_id=spotify_track_id)
            rb_id = track_meta.id
        elif rb_id:
            resp = self._request(
                "GET",
                f"{self._base_url}/v1/track/{rb_id}",
            )
            track_status = resp.status_code
            if resp.status_code == 404:
                return ReccoBeatsFetchResult(track=None, features=None, track_status_code=404)
            if resp.status_code >= 400:
                raise ReccoBeatsHTTPError(resp.status_code, body=resp.text)
            track_raw = _safe_json(resp) or {}
            if track_raw.get("id"):
                track_meta = self._parse_track_meta(track_raw, fallback_spotify_id=spotify_track_id)

        if not rb_id:
            return ReccoBeatsFetchResult(track=track_meta, features=None, track_raw=track_raw)

        features, features_raw, features_status = self.get_audio_features(rb_id)
        return ReccoBeatsFetchResult(
            track=track_meta,
            features=features,
            track_raw=track_raw,
            features_raw=features_raw,
            track_status_code=track_status,
            features_status_code=features_status,
        )


def _features_has_values(features: ReccoBeatsAudioFeatures) -> bool:
    return any(
        getattr(features, name) is not None
        for name in (
            "acousticness",
            "danceability",
            "energy",
            "instrumentalness",
            "tempo",
            "valence",
        )
    )


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_json(resp: httpx.Response) -> dict[str, Any] | None:
    if not resp.content:
        return None
    try:
        data = resp.json()
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _extract_track_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("content"), list):
        return [t for t in payload["content"] if isinstance(t, dict)]
    if isinstance(payload.get("tracks"), list):
        return [t for t in payload["tracks"] if isinstance(t, dict)]
    if payload.get("id"):
        return [payload]
    return []
