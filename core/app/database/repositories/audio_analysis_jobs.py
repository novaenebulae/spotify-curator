from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_audio import AudioAnalysisJob


class AudioAnalysisJobsRepository:
    def insert(self, session: Session, row: AudioAnalysisJob) -> AudioAnalysisJob:
        session.add(row)
        session.flush()
        return row

    def get(self, session: Session, row_id: int) -> AudioAnalysisJob | None:
        return session.get(AudioAnalysisJob, row_id)

    def get_latest_success_for_segment(
        self,
        session: Session,
        *,
        segment_id: int,
        pipeline_version: str,
        analysis_level: str = "essentia_lowlevel",
    ) -> AudioAnalysisJob | None:
        return session.scalars(
            select(AudioAnalysisJob)
            .where(
                AudioAnalysisJob.segment_id == segment_id,
                AudioAnalysisJob.analysis_level == analysis_level,
                AudioAnalysisJob.pipeline_version == pipeline_version,
                AudioAnalysisJob.status == "success",
            )
            .order_by(AudioAnalysisJob.id.desc())
            .limit(1)
        ).first()
