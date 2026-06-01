from app.audio.provider import TrackContext
from app.previews.matching import penalty_for_title, score_deezer_match
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
