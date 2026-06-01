"""Tests aligned with live ReccoBeats /v1/audio-features response shape."""

from __future__ import annotations

import json

import httpx

from app.reccobeats.client import ReccoBeatsClient

# Captured from https://api.reccobeats.com/v1/audio-features?ids=...
LIVE_BATCH_RESPONSE = {
    "content": [
        {
            "id": "c03ca78e-574c-474e-a283-7c70a2f751ba",
            "href": "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh",
            "isrc": "CH1401032103",
            "acousticness": 0.981,
            "danceability": 0.325,
            "energy": 0.159,
            "instrumentalness": 0.869,
            "key": 4,
            "liveness": 0.166,
            "loudness": -15.424,
            "mode": 0,
            "speechiness": 0.0464,
            "tempo": 67.091,
            "valence": 0.0399,
        }
    ]
}


def test_batch_client_parses_live_api_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio-features"
        return httpx.Response(
            200,
            content=json.dumps(LIVE_BATCH_RESPONSE).encode(),
            headers={"Content-Type": "application/json"},
        )

    client = ReccoBeatsClient(transport=httpx.MockTransport(handler))
    result = client.get_audio_features_batch(["4iV5W9uYEdYUVa79Axb7Rh", "missing_track"])

    assert len(result.entries) == 2
    found = result.entries[0]
    assert found.request_id == "4iV5W9uYEdYUVa79Axb7Rh"
    assert found.features is not None
    assert found.features.tempo == 67.091
    missing = result.entries[1]
    assert missing.request_id == "missing_track"
    assert missing.features is None
