from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.library import exports as export_service

router = APIRouter(prefix="/exports")


@router.post("/liked-tracks")
def export_liked_tracks(body: dict) -> dict:
    fmt = (body.get("format") or "json").lower()
    try:
        return export_service.export_liked_tracks(fmt=fmt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/playlists")
def export_playlists(body: dict) -> dict:
    fmt = (body.get("format") or "json").lower()
    try:
        return export_service.export_playlists(fmt=fmt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/snapshot/{snapshot_id}")
def export_snapshot(snapshot_id: str, body: dict | None = None) -> dict:
    body = body or {}
    fmt = (body.get("format") or "json").lower()
    try:
        return export_service.export_snapshot(snapshot_id=snapshot_id, fmt=fmt)
    except ValueError as e:
        msg = str(e)
        status = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=status, detail=msg) from e


@router.post("/diff")
def export_diff(body: dict) -> dict:
    from_id = body.get("from_snapshot_id")
    to_id = body.get("to_snapshot_id")
    if not from_id or not to_id:
        raise HTTPException(
            status_code=400,
            detail="from_snapshot_id and to_snapshot_id are required.",
        )
    fmt = (body.get("format") or "json").lower()
    try:
        return export_service.export_diff(
            from_snapshot_id=from_id,
            to_snapshot_id=to_id,
            fmt=fmt,
        )
    except ValueError as e:
        msg = str(e)
        status = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=status, detail=msg) from e
