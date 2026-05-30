from __future__ import annotations

import logging
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.sql_perf import get_track_search_perf, tracks_perf_logging_enabled

logger = logging.getLogger("tracks.perf")


class TracksPerfMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not tracks_perf_logging_enabled():
            return await call_next(request)
        path = request.url.path
        if request.method != "GET" or not path.endswith("/tracks"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        api_ms = (time.perf_counter() - start) * 1000.0

        payload_bytes = 0
        if hasattr(response, "body") and response.body:
            payload_bytes = len(response.body)

        perf = get_track_search_perf()
        extra = {}
        if perf is not None:
            extra = {
                "count_ms": round(perf.count_ms, 2),
                "page_ids_ms": round(perf.page_ids_ms, 2),
                "detail_ms": round(perf.detail_ms, 2),
                "artists_ms": round(perf.artists_ms, 2),
                "albums_ms": round(perf.albums_ms, 2),
                "playlists_ms": round(perf.playlists_ms, 2),
                "sql_ms": round(perf.sql_ms, 2),
                "sql_query_count": perf.sql_query_count,
            }

        logger.info(
            "GET /tracks perf api_total_ms=%.2f payload_bytes=%s query=%s %s",
            api_ms,
            payload_bytes,
            request.url.query,
            extra,
        )
        response.headers["X-Tracks-Perf-Ms"] = f"{api_ms:.2f}"
        if perf is not None:
            response.headers["X-Tracks-Sql-Count"] = str(perf.sql_query_count)
            response.headers["X-Tracks-Sql-Ms"] = f"{perf.sql_ms:.2f}"
        return response
