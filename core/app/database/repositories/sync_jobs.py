from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.database.models_playlists_engine import SyncJob, SyncLog


class SyncJobsRepository:
    def create(
        self,
        session: Session,
        *,
        generated_playlist_id: int,
        sync_mode: str,
        target_spotify_playlist_id: str | None,
        diff_json: str,
        dry_run: bool = True,
        status: str = "previewed",
    ) -> SyncJob:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        row = SyncJob(
            generated_playlist_id=generated_playlist_id,
            sync_mode=sync_mode,
            target_spotify_playlist_id=target_spotify_playlist_id,
            dry_run=dry_run,
            status=status,
            diff_json=diff_json,
            created_at=now,
            finished_at=now,
        )
        session.add(row)
        session.flush()
        return row

    def get(self, session: Session, sync_job_id: int) -> SyncJob | None:
        return session.get(SyncJob, sync_job_id)

    def add_log(
        self,
        session: Session,
        *,
        sync_job_id: int,
        level: str,
        message: str,
        context_json: str | None = None,
    ) -> SyncLog:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        row = SyncLog(
            sync_job_id=sync_job_id,
            level=level,
            message=message,
            context_json=context_json,
            created_at=now,
        )
        session.add(row)
        session.flush()
        return row
