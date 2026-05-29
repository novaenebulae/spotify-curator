from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.library.snapshots import SnapshotService

router = APIRouter(prefix="/library/snapshots")
_svc = SnapshotService()


@router.post("/create")
def create_snapshot(body: dict) -> dict:
    snapshot_type = body.get("type")
    if snapshot_type not in ("full", "liked", "playlists"):
        raise HTTPException(status_code=400, detail="Invalid snapshot type.")
    snapshot_id = _svc.create_snapshot(snapshot_type)
    return {"snapshot_id": snapshot_id, "status": "completed"}


@router.get("")
def list_snapshots() -> list[dict]:
    return _svc.list_snapshots()


@router.post("/diff")
def diff_snapshots(body: dict) -> dict:
    from_id = body.get("from_snapshot_id")
    to_id = body.get("to_snapshot_id")
    if not from_id or not to_id:
        raise HTTPException(
            status_code=400,
            detail="from_snapshot_id and to_snapshot_id are required.",
        )
    try:
        return _svc.diff(from_id, to_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{snapshot_id}")
def get_snapshot(snapshot_id: str) -> dict:
    s = _svc.get_snapshot(snapshot_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Snapshot not found.")
    return s

