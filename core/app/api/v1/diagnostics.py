from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()


def _dir_status(path_str: str) -> dict:
    p = Path(path_str)
    return {
        "path": str(p),
        "exists": p.exists(),
        "is_dir": p.is_dir(),
        "writable": os.access(p, os.W_OK) if p.exists() else False,
    }


@router.get("/diagnostics")
def diagnostics() -> dict:
    return {
        "env": {
            "database_url_set": bool(os.getenv("DATABASE_URL")),
            "cache_dir": os.getenv("CACHE_DIR", "/app/cache"),
            "models_dir": os.getenv("MODELS_DIR", "/app/models"),
            "logs_dir": os.getenv("LOGS_DIR", "/app/logs"),
        },
        "paths": {
            "data": _dir_status("/app/data"),
            "cache": _dir_status(os.getenv("CACHE_DIR", "/app/cache")),
            "models": _dir_status(os.getenv("MODELS_DIR", "/app/models")),
            "logs": _dir_status(os.getenv("LOGS_DIR", "/app/logs")),
        },
    }

