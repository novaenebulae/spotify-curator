import json
from pathlib import Path

import httpx

from app.audio.provider import TrackContext
from app.previews.deezer_client import DeezerClient
from app.previews.deezer_provider import (
    MATCH_STRATEGY_ISRC_EXACT,
    MATCH_STRATEGY_METADATA_FUZZY,
    DeezerPreviewProvider,
)

_FIXTURES = Path(__file__).parent / "fixtures"


def _track() -> TrackContext:
    return TrackContext(
        track_id=1,
        title="Harder Better Faster Stronger",
        primary_artist="Daft Punk",
        album="Discovery",
        duration_ms=224000,
        isrc="GBDUW0100057",
    )


def _provider(
    *,
    isrc_body: dict | None = None,
    isrc_status: int = 200,
    search_body: dict | None = None,
) -> DeezerPreviewProvider:
    search = search_body or json.loads((_FIXTURES / "deezer_search_response.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if "/track/isrc:" in request.url.path:
            if isrc_status == 404:
                return httpx.Response(404, json={"error": {"message": "Not found"}})
            if isrc_body is not None:
                return httpx.Response(200, json=isrc_body)
            return httpx.Response(404, json={"error": {"message": "Not found"}})
        if "/search/track" in request.url.path:
            return httpx.Response(200, json=search)
        return httpx.Response(404, json={"error": {"message": "unknown"}})

    return DeezerPreviewProvider(client=DeezerClient(transport=httpx.MockTransport(handler)))


def test_resolve_preview_isrc_exact_skips_search() -> None:
    isrc_body = json.loads((_FIXTURES / "deezer_isrc_response.json").read_text())
    search_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "/search/track" in request.url.path:
            search_calls.append(request.url.path)
        if "/track/isrc:" in request.url.path:
            return httpx.Response(200, json=isrc_body)
        return httpx.Response(200, json=json.loads((_FIXTURES / "deezer_search_response.json").read_text()))

    provider = DeezerPreviewProvider(client=DeezerClient(transport=httpx.MockTransport(handler)))
    cand = provider.resolve_preview(_track())
    assert cand.is_available
    assert cand.provider_track_id == "3135556"
    assert cand.match_confidence == 1.0
    assert cand.match_strategy == MATCH_STRATEGY_ISRC_EXACT
    assert search_calls == []


def test_resolve_preview_isrc_404_falls_back_to_search() -> None:
    cand = _provider(isrc_status=404).resolve_preview(_track())
    assert cand.is_available
    assert cand.provider_track_id == "3135556"
    assert cand.match_strategy == MATCH_STRATEGY_ISRC_EXACT


def test_resolve_preview_isrc_no_preview_falls_back_to_search() -> None:
    isrc_body = json.loads((_FIXTURES / "deezer_isrc_no_preview_response.json").read_text())
    cand = _provider(isrc_body=isrc_body).resolve_preview(_track())
    assert cand.is_available
    assert cand.provider_track_id == "3135556"
    assert cand.match_strategy in {MATCH_STRATEGY_ISRC_EXACT, MATCH_STRATEGY_METADATA_FUZZY}


def test_resolve_preview_fuzzy_picks_studio_track_without_isrc() -> None:
    track = TrackContext(
        track_id=2,
        title="Harder Better Faster Stronger",
        primary_artist="Daft Punk",
        album="Discovery",
        duration_ms=224000,
        isrc=None,
    )
    cand = _provider(isrc_status=404).resolve_preview(track)
    assert cand.is_available
    assert cand.provider_track_id == "3135556"
    assert cand.match_strategy == MATCH_STRATEGY_METADATA_FUZZY


def test_resolve_preview_picks_studio_track() -> None:
    """Backward-compatible alias: fuzzy path when ISRC endpoint unavailable."""
    cand = _provider(isrc_status=404).resolve_preview(_track())
    assert cand.is_available
    assert cand.provider_track_id == "3135556"
    assert cand.preview_url is not None
