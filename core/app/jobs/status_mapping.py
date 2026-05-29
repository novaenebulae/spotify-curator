from __future__ import annotations

_DB_TO_API: dict[str, str] = {
    "queued": "pending",
    "running": "running",
    "succeeded": "success",
    "failed": "failed",
    "rate_limited": "rate_limited",
    "cancelled": "cancelled",
}


def map_job_status(db_status: str) -> str:
    return _DB_TO_API.get(db_status, db_status)
