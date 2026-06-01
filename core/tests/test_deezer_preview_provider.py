import json
from pathlib import Path

import httpx

from app.audio.provider import TrackContext
from app.previews.deezer_client import DeezerClient
from app.previews.deezer_provider import DeezerPreviewProvider


def test_resolve_preview_picks_studio_track() -> None:
    fixture = Path(__file__).parent / "fixtures" / "deezer_search_response.json"
    body = json.loads(fixture.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)
    client = DeezerClient(transport=transport)
    provider = DeezerPreviewProvider(client=client)
    track = TrackContext(
        track_id=1,
        title="Harder Better Faster Stronger",
        primary_artist="Daft Punk",
        album="Discovery",
        duration_ms=224000,
        isrc="GBDUW0100057",
    )
    cand = provider.resolve_preview(track)
    assert cand.is_available
    assert cand.provider_track_id == "3135556"
    assert cand.preview_url is not None
