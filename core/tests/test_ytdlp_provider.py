from __future__ import annotations

from app.audio.ytdlp_cmd import build_download_section_command, build_search_command


def test_search_command_noplaylist() -> None:
    cmd = build_search_command("Artist Title audio")
    assert "yt-dlp" in cmd.argv[0]
    assert "--no-playlist" in cmd.argv
    assert any("ytsearch" in a for a in cmd.argv)


def test_download_section_command() -> None:
    cmd = build_download_section_command(
        "https://example.com/watch?v=x",
        start_seconds=10.0,
        end_seconds=25.0,
        output_path="/tmp/out.%(ext)s",
        audio_format="bestaudio/best",
    )
    assert "--download-sections" in cmd.argv
    assert "*10.000-25.000" in cmd.argv
    assert "--no-playlist" in cmd.argv
