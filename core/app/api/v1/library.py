from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.library.actions import LibraryActionsService
from app.library.duplicates import DuplicateDetectionService
from app.library.missing import MissingTracksService
from app.library.summary import LibrarySummaryService

router = APIRouter(prefix="/library", tags=["library"])
_duplicates = DuplicateDetectionService()
_missing = MissingTracksService()
_actions = LibraryActionsService()
_summary = LibrarySummaryService()


@router.get("/summary")
def library_summary() -> dict:
    return _summary.get_summary()


@router.get("/duplicates")
def list_duplicates(
    strategy: Annotated[str, Query()] = "isrc",
    min_confidence: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    return _duplicates.list_duplicates(
        strategy=strategy,
        min_confidence=min_confidence,
        page=page,
        page_size=page_size,
    )


@router.get("/missing-tracks")
def list_missing_tracks(
    snapshot_id: Annotated[str | None, Query()] = None,
    from_snapshot_id: Annotated[str | None, Query()] = None,
    to_snapshot_id: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict:
    return _missing.list_missing(
        snapshot_id=snapshot_id,
        from_snapshot_id=from_snapshot_id,
        to_snapshot_id=to_snapshot_id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.post("/actions/dry-run")
def dry_run_action(body: dict) -> dict:
    return _actions.dry_run(
        action_type=body.get("action_type", ""),
        track_ids=body.get("track_ids"),
        filter=body.get("filter"),
        options=body.get("options"),
    )


@router.get("/actions")
def list_actions(
    action_type: Annotated[str | None, Query()] = None,
    dry_run: Annotated[bool | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    return _actions.list_actions(
        action_type=action_type,
        dry_run=dry_run,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/actions/{action_id}")
def get_action(action_id: int) -> dict:
    return _actions.get_action(action_id)
