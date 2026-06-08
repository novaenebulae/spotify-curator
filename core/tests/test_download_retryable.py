from __future__ import annotations

from sqlalchemy.exc import OperationalError

from app.audio.errors import FfmpegError, YtDlpError, is_download_failure_retryable


def test_audio_tool_error_retryable_flag() -> None:
    assert is_download_failure_retryable(
        YtDlpError("YTDLP_TIMEOUT", "yt-dlp download timed out", retryable=True)
    )
    assert not is_download_failure_retryable(
        YtDlpError("YTDLP_NOT_FOUND", "yt-dlp binary not found on PATH")
    )


def test_sqlite_locked_is_retryable() -> None:
    assert is_download_failure_retryable(
        OperationalError("UPDATE jobs", {}, Exception("database is locked"))
    )


def test_missing_file_is_retryable() -> None:
    assert is_download_failure_retryable(
        FileNotFoundError("No such file or directory: '/app/temp-audio/x.wav'")
    )


def test_ffmpeg_timeout_is_retryable() -> None:
    assert is_download_failure_retryable(
        FfmpegError("FFMPEG_TIMEOUT", "ffmpeg timed out", retryable=True)
    )
