from __future__ import annotations

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
