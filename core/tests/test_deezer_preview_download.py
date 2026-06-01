import httpx

from app.audio.deezer_preview_download import download_deezer_preview_segment
from app.audio.provider import PlannedSegment, TrackContext


def test_download_deezer_preview_mock(audio_db, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    content = b"\x00" * 1000

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=content)

    track = TrackContext(1, "T", "A", None, 180000)
    seg = PlannedSegment(
        segment_type="DEEZER_PREVIEW",
        start_seconds=0,
        end_seconds=15,
        duration_seconds=15,
        strategy="hybrid",
        source="deezer_preview",
        source_quality="deezer_preview_30s",
    )
    import shutil

    if not shutil.which("ffmpeg"):
        return
    rel, digest = download_deezer_preview_segment(
        track,
        job_id="job1",
        segment=seg,
        preview_url="https://example.com/preview.mp3",
        transport=httpx.MockTransport(handler),
    )
    assert rel
    assert digest
