from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_audio import AudioDownloadJob


class AudioDownloadJobsRepository:
    def get(self, session: Session, row_id: int) -> AudioDownloadJob | None:
        return session.get(AudioDownloadJob, row_id)

    def get_latest_for_track(self, session: Session, track_id: int) -> AudioDownloadJob | None:
        return session.execute(
            select(AudioDownloadJob)
            .where(AudioDownloadJob.track_id == track_id)
            .order_by(AudioDownloadJob.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def insert(self, session: Session, row: AudioDownloadJob) -> AudioDownloadJob:
        session.add(row)
        session.flush()
        return row
