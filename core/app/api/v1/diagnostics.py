from __future__ import annotations

from fastapi import APIRouter

from app.observability.diagnostics import legacy_diagnostics_payload

router = APIRouter()


@router.get("/diagnostics")
def diagnostics() -> dict:
    """Legacy alias; prefer /runtime/docker/checks for persisted checks."""
    return legacy_diagnostics_payload()
