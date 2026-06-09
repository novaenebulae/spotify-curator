from __future__ import annotations

from sqlalchemy.exc import OperationalError

LOCAL_ANALYSIS_UNAVAILABLE = "LOCAL_ANALYSIS_UNAVAILABLE"


class AudioToolError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        self.code = code
        self.retryable = retryable
        super().__init__(message)


class FfmpegError(AudioToolError):
    pass


class YtDlpError(AudioToolError):
    pass


class EssentiaError(AudioToolError):
    pass


def _is_sqlite_locked(exc: BaseException) -> bool:
    if not isinstance(exc, OperationalError):
        return False
    orig = getattr(exc, "orig", None)
    return orig is not None and "locked" in str(orig).lower()


def is_youtube_transient_error(message: str) -> bool:
    lowered = message.lower()
    needles = (
        "not a bot",
        "sign in to confirm",
        "try again later",
        "http error 403",
        "http error 429",
        "http error 503",
        "too many requests",
        "rate-limit",
        "rate limit",
        "challenge",
        "googlevideo.com",
        "unable to download",
        "fragment",
        "no youtube source",
        "timed out",
        "timeout",
    )
    return any(needle in lowered for needle in needles)


def is_download_failure_retryable(exc: BaseException) -> bool:
    """Whether an audio download error should return the job item to pending."""
    if isinstance(exc, AudioToolError):
        return exc.retryable
    if isinstance(exc, OperationalError):
        return _is_sqlite_locked(exc)
    message = str(exc)
    lowered = message.lower()
    if "database is locked" in lowered:
        return True
    if "no such file or directory" in lowered:
        return True
    if is_youtube_transient_error(message):
        return True
    return "timeout" in lowered or "rate" in lowered
