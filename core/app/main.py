from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
)
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.database.init_db import init_db
from app.observability.errors import register_exception_handlers
from app.observability.tracks_perf_middleware import TracksPerfMiddleware
from app.settings.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger = logging.getLogger("spotify-curator-core")
    logger.info("Starting spotify-curator-core (version %s)", settings.app_version)
    try:
        init_db()
        logger.info("Database migrations applied")
    except Exception:
        logger.exception("Database migration failed during startup")
        raise
    logger.info(
        "Application startup complete — API ready at http://%s:%s%s",
        settings.core_host,
        settings.core_port,
        settings.api_v1_prefix,
    )
    yield
    logger.info("Shutting down spotify-curator-core")


def create_app() -> FastAPI:
    app = FastAPI(title="spotify-curator-core", lifespan=lifespan)

    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "tauri://localhost",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.add_middleware(TracksPerfMiddleware)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
