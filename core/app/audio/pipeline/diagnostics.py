from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.pipeline.constants import (
    ITEM_TYPE_ANALYSIS_PIPELINE_STAGE,
    STAGE_AUDIO_CLEANUP,
    STAGE_FEATURE_AGGREGATION,
)
from app.database.engine import get_engine
from app.database.repositories.job_items import JobItemsRepository

_NON_TERMINAL = frozenset({"pending", "running", "blocked", "rate_limited"})


def pipeline_non_terminal_items(job_id: str, *, limit: int = 50) -> list[dict]:
    """Summarize pipeline items that may block job completion (for API diagnostics)."""
    engine = get_engine()
    repo = JobItemsRepository()
    with Session(engine) as session:
        rows = repo.list_for_job(session, job_id, limit=10_000, offset=0)
    out: list[dict] = []
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    for row in rows:
        if row.item_type != ITEM_TYPE_ANALYSIS_PIPELINE_STAGE:
            continue
        if row.status not in _NON_TERMINAL:
            continue
        out.append(
            {
                "id": row.id,
                "stage_name": row.stage_name,
                "status": row.status,
                "track_id": row.track_id,
                "segment_id": row.segment_id,
                "error_code": row.error_code,
                "locked_by": row.locked_by,
                "next_retry_at": row.next_retry_at.isoformat() if row.next_retry_at else None,
                "retry_due": bool(
                    row.next_retry_at is not None and row.next_retry_at <= now
                ),
            }
        )
    out.sort(key=lambda r: (str(r.get("stage_name")), str(r.get("status"))))
    return out[:limit]


def pipeline_stuck_hint(job_id: str) -> str | None:
    """Heuristic hint when a pipeline job appears stalled."""
    items = pipeline_non_terminal_items(job_id, limit=100)
    if not items:
        return None

    agg_pending = [
        i
        for i in items
        if i.get("stage_name") == STAGE_FEATURE_AGGREGATION and i.get("status") == "pending"
    ]
    cleanup_pending = [
        i
        for i in items
        if i.get("stage_name") == STAGE_AUDIO_CLEANUP and i.get("status") == "pending"
    ]
    cleanup_retry = [
        i
        for i in cleanup_pending
        if i.get("error_code") == "SEGMENT_CONSUMER_PENDING" and i.get("retry_due")
    ]
    running_stale = [i for i in items if i.get("status") == "running" and i.get("locked_by")]

    if cleanup_retry:
        return (
            "audio_cleanup pending retry (SEGMENT_CONSUMER_PENDING); "
            "wait for pipeline tick or cancel job"
        )
    if agg_pending and not any(
        i.get("stage_name") in ("essentia_lowlevel", "essentia_tensorflow")
        and i.get("status") in ("pending", "running", "blocked")
        for i in items
    ):
        return "feature_aggregation pending with upstream complete; pipeline tick should run it"
    if running_stale:
        return "segment stage locked (running); stale lock release runs on pipeline tick"
    if any(i.get("status") == "blocked" for i in items):
        return "blocked stages waiting on dependencies; check upstream segment_download success"
    return "non_terminal pipeline items remain; inspect non_terminal_items list"
