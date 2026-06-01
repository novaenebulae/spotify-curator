from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models_audio import AudioAnalysisJob


class AudioAnalysisJobsRepository:
    def insert(self, session: Session, row: AudioAnalysisJob) -> AudioAnalysisJob:
        session.add(row)
        session.flush()
        return row

    def get(self, session: Session, row_id: int) -> AudioAnalysisJob | None:
        return session.get(AudioAnalysisJob, row_id)
