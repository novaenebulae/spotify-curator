from app.audio.provider import TrackContext
from app.previews.matching import (
    is_isrc_exact_match,
    penalty_for_title,
    score_deezer_match,
    score_isrc_exact_match,
)
from app.previews.schemas import DeezerTrackResult


def test_score_prefers_non_live_match() -> None:
    track = TrackContext(
        track_id=1,
        title="Harder Better Faster Stronger",
        primary_artist="Daft Punk",
        album="Discovery",
        duration_ms=224000,
        isrc="GBDUW0100057",
    )
    studio = DeezerTrackResult(
        id="1",
        title="Harder Better Faster Stronger",
        artist_name="Daft Punk",
        album_title="Discovery",
        preview_url="https://example/p.mp3",
        duration_seconds=224.0,
        link="https://deezer/track/1",
        isrc="GBDUW0100057",
    )
    live = DeezerTrackResult(
        id="2",
        title="Harder Better Faster Stronger (Live)",
        artist_name="Daft Punk",
        album_title=None,
        preview_url="https://example/live.mp3",
        duration_seconds=300.0,
        link=None,
    )
    s_studio, c_studio = score_deezer_match(track, studio)
    s_live, c_live = score_deezer_match(track, live)
    assert s_studio > s_live
    assert c_studio > c_live


def test_live_penalty() -> None:
    assert penalty_for_title("Song (Live at Wembley)") >= 0.25


def test_isrc_exact_match_returns_full_confidence_despite_weak_title() -> None:
    track = TrackContext(
        track_id=3,
        title="Completely Different Title",
        primary_artist="Other Artist",
        album=None,
        duration_ms=224000,
        isrc="GBDUW0100057",
    )
    candidate = DeezerTrackResult(
        id="99",
        title="Wrong Title On Deezer",
        artist_name="Wrong Artist",
        album_title=None,
        preview_url="https://example/p.mp3",
        duration_seconds=999.0,
        link=None,
        isrc="gbduw0100057",
    )
    assert is_isrc_exact_match(track, candidate)
    score, conf = score_isrc_exact_match(track, candidate)
    assert score == 1.0
    assert conf == 1.0
    fuzzy_score, fuzzy_conf = score_deezer_match(track, candidate)
    assert fuzzy_score == 1.0
    assert fuzzy_conf == 1.0
