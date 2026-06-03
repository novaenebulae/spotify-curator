from __future__ import annotations

import os
from pathlib import Path

DOCKER_DATABASE_URL = "sqlite:////app/data/spotify_curator.sqlite"


def running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def is_windows_sqlite_url(database_url: str) -> bool:
    if not database_url.startswith("sqlite:///"):
        return False
    rest = database_url.removeprefix("sqlite:///")
    return len(rest) >= 2 and rest[0].isalpha() and rest[1] == ":"


def resolve_database_url() -> str:
    """Pick SQLite URL; in Docker, ignore host Windows paths that break volume mounts."""
    url = os.getenv("DATABASE_URL", DOCKER_DATABASE_URL).strip() or DOCKER_DATABASE_URL
    if running_in_docker() and is_windows_sqlite_url(url):
        return DOCKER_DATABASE_URL
    return url
