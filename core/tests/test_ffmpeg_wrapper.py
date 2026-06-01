from __future__ import annotations

from pathlib import Path

from app.audio.ffmpeg import build_wav_convert_command


def test_ffmpeg_wav_command_shape() -> None:
    cmd = build_wav_convert_command(Path("/in.webm"), Path("/out.wav"))
    assert cmd.argv[0] == "ffmpeg"
    assert "pcm_s16le" in cmd.argv
    assert "44100" in cmd.argv
    assert str(cmd.output_path).endswith(".wav")
