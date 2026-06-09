from __future__ import annotations

from app.previews.deezer_audit_verdicts import (
    VERDICT_MISMATCH,
    VERDICT_OK,
    classify_deezer_audit_verdict,
)
from app.previews.schemas import DeezerTrackResult


class _PreviewStub:
    def __init__(self, *, provider_track_id: str | None, match_strategy: str | None, match_confidence: float | None):
        self.provider_track_id = provider_track_id
        self.match_strategy = match_strategy
        self.match_confidence = match_confidence
        self.title = "Stored Title"


def test_classify_verdict_ok_when_ids_match() -> None:
    preview = _PreviewStub(provider_track_id="123", match_strategy="isrc_exact", match_confidence=1.0)
    isrc_hit = DeezerTrackResult(
        id="123",
        title="Canonical",
        artist_name="Artist",
        album_title=None,
        preview_url="https://example/p.mp3",
        duration_seconds=200.0,
        link=None,
        isrc="USRC1",
    )
    verdict, details = classify_deezer_audit_verdict(
        preview=preview, isrc_hit=isrc_hit, stored_confidence=1.0
    )
    assert verdict == VERDICT_OK
    assert details is None


def test_classify_verdict_mismatch_when_ids_differ() -> None:
    preview = _PreviewStub(provider_track_id="999", match_strategy="metadata_fuzzy", match_confidence=0.7)
    isrc_hit = DeezerTrackResult(
        id="123",
        title="Canonical",
        artist_name="Artist",
        album_title=None,
        preview_url="https://example/p.mp3",
        duration_seconds=200.0,
        link=None,
        isrc="USRC1",
    )
    verdict, details = classify_deezer_audit_verdict(
        preview=preview, isrc_hit=isrc_hit, stored_confidence=0.7
    )
    assert verdict == VERDICT_MISMATCH
    assert details is not None
