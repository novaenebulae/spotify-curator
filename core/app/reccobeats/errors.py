from __future__ import annotations


class ReccoBeatsError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "RECCOBEATS_ERROR",
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable


class ReccoBeatsNotFound(ReccoBeatsError):
    def __init__(self, message: str = "Track not found on ReccoBeats") -> None:
        super().__init__(message, code="RECCOBEATS_NOT_FOUND", status_code=404, retryable=False)


class ReccoBeatsRateLimited(ReccoBeatsError):
    def __init__(self, retry_after_seconds: int | None = None) -> None:
        super().__init__(
            "ReccoBeats rate limited",
            code="RECCOBEATS_RATE_LIMITED",
            status_code=429,
            retryable=True,
        )
        self.retry_after_seconds = retry_after_seconds


class ReccoBeatsTimeout(ReccoBeatsError):
    def __init__(self, message: str = "ReccoBeats request timed out") -> None:
        super().__init__(message, code="RECCOBEATS_TIMEOUT", retryable=True)


class ReccoBeatsHTTPError(ReccoBeatsError):
    def __init__(self, status_code: int, body: str | None = None) -> None:
        super().__init__(
            f"ReccoBeats HTTP {status_code}",
            code="RECCOBEATS_HTTP_ERROR",
            status_code=status_code,
            retryable=500 <= status_code < 600,
        )
        self.body = body
