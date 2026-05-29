from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.spotify.client import SpotifyAuthError, SpotifyRateLimited


class ApiError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.retryable = retryable


def error_payload(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "retryable": retryable,
        }
    }


def _http_status_to_code(status_code: int) -> str:
    if status_code == 400:
        return "VALIDATION_ERROR"
    if status_code == 401:
        return "UNAUTHORIZED_SPOTIFY"
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 409:
        return "CONFLICT"
    if status_code == 429:
        return "SPOTIFY_RATE_LIMITED"
    return "INTERNAL_ERROR"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                retryable=exc.retryable,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            message = str(detail.get("message") or detail)
            details = detail if isinstance(detail, dict) else {}
        else:
            message = str(detail)
            details = {}
        code = _http_status_to_code(exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                code=code,
                message=message,
                details=details,
                retryable=exc.status_code == 429,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=error_payload(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": exc.errors()},
                retryable=False,
            ),
        )

    @app.exception_handler(SpotifyAuthError)
    async def spotify_auth_handler(_request: Request, exc: SpotifyAuthError) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content=error_payload(
                code="UNAUTHORIZED_SPOTIFY",
                message=str(exc),
                retryable=False,
            ),
        )

    @app.exception_handler(SpotifyRateLimited)
    async def spotify_rate_limited_handler(
        _request: Request, exc: SpotifyRateLimited
    ) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=error_payload(
                code="SPOTIFY_RATE_LIMITED",
                message=str(exc),
                details={"retry_after_seconds": exc.retry_after_seconds},
                retryable=True,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_payload(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details={"type": type(exc).__name__},
                retryable=False,
            ),
        )
