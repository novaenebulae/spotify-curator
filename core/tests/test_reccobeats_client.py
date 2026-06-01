from __future__ import annotations

import json

import httpx
import pytest

from app.reccobeats.client import ReccoBeatsClient
from app.reccobeats.errors import (
    ReccoBeatsError,
    ReccoBeatsHTTPError,
    ReccoBeatsNotFound,
    ReccoBeatsRateLimited,
    ReccoBeatsTimeout,
)
from tests.fixtures.reccobeats_responses import (
    RECCOBEATS_TRACK_ID,
    SAMPLE_FEATURES,
    SAMPLE_TRACK,
    SPOTIFY_TRACK_ID,
    batch_response_for_spotify_ids,
)


def _json_response(status: int, payload: dict | list | None) -> httpx.Response:
    content = json.dumps(payload).encode() if payload is not None else b""
    return httpx.Response(status, content=content, headers={"Content-Type": "application/json"})


def test_fetch_track_features_success() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/v1/track" and request.method == "GET":
            return _json_response(200, {"content": [SAMPLE_TRACK]})
        if request.url.path == f"/v1/track/{RECCOBEATS_TRACK_ID}/audio-features":
            return _json_response(200, SAMPLE_FEATURES)
        return _json_response(404, {"error": "not found"})

    client = ReccoBeatsClient(
        base_url="https://api.reccobeats.com",
        transport=httpx.MockTransport(handler),
    )
    result = client.fetch_track_features(spotify_track_id=SPOTIFY_TRACK_ID)

    assert result.track is not None
    assert result.track.id == RECCOBEATS_TRACK_ID
    assert result.features is not None
    assert result.features.tempo == 93.5
    assert result.features.energy == 0.72
    assert len(calls) == 2


def test_fetch_track_not_found() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return _json_response(404, {"error": "Track not found"})

    client = ReccoBeatsClient(transport=httpx.MockTransport(handler))
    result = client.fetch_track_features(spotify_track_id="missing")

    assert result.track is None
    assert result.features is None
    assert result.track_status_code == 404


def test_get_audio_features_not_found_raises() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return _json_response(404, {"error": "Track not found"})

    client = ReccoBeatsClient(transport=httpx.MockTransport(handler))
    with pytest.raises(ReccoBeatsNotFound):
        client.get_audio_features("unknown-id")


def test_rate_limit_then_success() -> None:
    attempts = {"count": 0}
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/track":
            attempts["count"] += 1
            if attempts["count"] == 1:
                return httpx.Response(429, headers={"Retry-After": "1"})
            return _json_response(200, {"content": [SAMPLE_TRACK]})
        if request.url.path.endswith("/audio-features"):
            return _json_response(200, SAMPLE_FEATURES)
        return _json_response(404, None)

    client = ReccoBeatsClient(
        transport=httpx.MockTransport(handler),
        max_retries=3,
        sleeper=lambda s: sleeps.append(s),
    )
    result = client.fetch_track_features(spotify_track_id=SPOTIFY_TRACK_ID)

    assert result.features is not None
    assert attempts["count"] == 2
    assert sleeps == [1.0]


def test_rate_limit_exhausted_raises() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "1"})

    client = ReccoBeatsClient(
        transport=httpx.MockTransport(handler),
        max_retries=1,
        sleeper=lambda _: None,
    )
    with pytest.raises(ReccoBeatsRateLimited):
        client.fetch_track_features(spotify_track_id=SPOTIFY_TRACK_ID)


def test_timeout_retries_then_raises() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    client = ReccoBeatsClient(
        transport=httpx.MockTransport(handler),
        max_retries=1,
        sleeper=lambda _: None,
    )
    with pytest.raises(ReccoBeatsTimeout):
        client.fetch_track_features(spotify_track_id=SPOTIFY_TRACK_ID)


def test_empty_response_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/track":
            return httpx.Response(200, content=b"")
        return httpx.Response(200, content=b"")

    client = ReccoBeatsClient(transport=httpx.MockTransport(handler))
    result = client.fetch_track_features(spotify_track_id=SPOTIFY_TRACK_ID)

    assert result.track is None


def test_get_audio_features_batch_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/audio-features":
            ids = request.url.params.get("ids", "").split(",")
            return _json_response(200, batch_response_for_spotify_ids(ids))
        return _json_response(404, None)

    client = ReccoBeatsClient(transport=httpx.MockTransport(handler))
    result = client.get_audio_features_batch([SPOTIFY_TRACK_ID, "other_id"])

    assert result.status_code == 200
    assert len(result.entries) == 2
    assert result.entries[0].features is not None
    assert result.entries[0].features.tempo == 93.5


def test_get_audio_features_batch_empty_raises() -> None:
    client = ReccoBeatsClient(transport=httpx.MockTransport(lambda _: _json_response(200, {})))
    with pytest.raises(ReccoBeatsError) as exc:
        client.get_audio_features_batch([])
    assert exc.value.code == "RECCOBEATS_BATCH_EMPTY"


def test_get_audio_features_batch_too_large_raises() -> None:
    client = ReccoBeatsClient(transport=httpx.MockTransport(lambda _: _json_response(200, {})))
    with pytest.raises(ReccoBeatsError) as exc:
        client.get_audio_features_batch(["id"] * 41)
    assert exc.value.code == "RECCOBEATS_BATCH_TOO_LARGE"


def test_get_audio_features_batch_rate_limit_then_success() -> None:
    attempts = {"n": 0}
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path != "/v1/audio-features":
            return _json_response(404, None)
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        ids = request.url.params.get("ids", "").split(",")
        return _json_response(200, batch_response_for_spotify_ids(ids))

    client = ReccoBeatsClient(
        transport=httpx.MockTransport(handler),
        max_retries=3,
        sleeper=lambda s: sleeps.append(s),
    )
    result = client.get_audio_features_batch([SPOTIFY_TRACK_ID])
    assert result.entries[0].features is not None
    assert attempts["n"] == 2
    assert sleeps == [1.0]


def test_http_500_retries_then_raises() -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, content=b"server error")

    client = ReccoBeatsClient(
        transport=httpx.MockTransport(handler),
        max_retries=1,
        sleeper=lambda _: None,
    )
    with pytest.raises(ReccoBeatsHTTPError) as exc:
        client.fetch_track_features(spotify_track_id=SPOTIFY_TRACK_ID)
    assert exc.value.status_code == 500
    assert calls["n"] == 2
