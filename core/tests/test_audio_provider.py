from __future__ import annotations

from app.audio.provider import TrackContext
from app.audio.test_provider import StubAudioProvider


def test_test_audio_provider_resolve_and_segments(tmp_path) -> None:
    wav = tmp_path / "tiny.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 44)
    provider = StubAudioProvider(fixture_wav=wav)
    ctx = TrackContext(
        track_id=1,
        title="Song",
        primary_artist="Artist",
        album=None,
        duration_ms=180_000,
    )
    candidates = provider.resolve(ctx)
    assert len(candidates) == 1
    assert candidates[0].selected
    segs = provider.get_segments(ctx, "abc_default")
    assert segs
    rel, h = provider.materialize_segment(ctx, job_id="job1", segment=segs[0])
    assert rel.startswith("audio_segments/")
    assert h == "test-hash"
