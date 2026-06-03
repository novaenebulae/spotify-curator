from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.observability.errors import ApiError
from app.playlists.sync_dry_run import SyncDryRunService

router = APIRouter(prefix="/sync", tags=["sync"])
_service = SyncDryRunService()


class DryRunRequest(BaseModel):
    generated_playlist_id: int
    target_spotify_playlist_id: str | None = None
    sync_mode: str = "replace"


@router.post("/dry-run")
def sync_dry_run(body: DryRunRequest) -> dict:
    engine = get_engine()
    with Session(engine) as session:
        return _service.run(
            session,
            generated_playlist_id=body.generated_playlist_id,
            target_spotify_playlist_id=body.target_spotify_playlist_id,
            sync_mode=body.sync_mode,
        )


@router.get("/jobs/{sync_job_id}")
def get_sync_job(sync_job_id: int) -> dict:
    engine = get_engine()
    with Session(engine) as session:
        result = _service.get_job(session, sync_job_id)
        if result is None:
            raise ApiError(status_code=404, code="SYNC_JOB_NOT_FOUND", message="Sync job not found")
        return result
