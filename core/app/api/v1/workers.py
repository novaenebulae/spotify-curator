from __future__ import annotations

from fastapi import APIRouter, Query

from app.workers.heartbeat import WorkerHeartbeatService

router = APIRouter(prefix="/workers")
_heartbeat = WorkerHeartbeatService()


@router.get("")
def list_workers(worker_type: str | None = Query(default=None)) -> dict:
    items = _heartbeat.list_active(worker_type=worker_type)
    return {"workers": items, "count": len(items)}
