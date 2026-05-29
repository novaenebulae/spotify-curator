from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.database.init_db import init_db
from app.settings.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="spotify-curator-core")

    # Enable CORS for local UI dev server (SvelteKit) and future Tauri webview origins.
    # The API is still bound to 127.0.0.1 via docker-compose publish rules.
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

    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    return app


app = create_app()

