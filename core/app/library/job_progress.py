from __future__ import annotations

from sqlalchemy.orm import Session

from app.jobs.service import JobService

# Update job row at most every N items to limit SQLite writes while keeping UI responsive.
PROGRESS_UPDATE_EVERY = 25


def report_job_progress(
    session: Session,
    jobs: JobService,
    job_id: str,
    *,
    idx: int = 0,
    force: bool = False,
    every: int = PROGRESS_UPDATE_EVERY,
    **kwargs: object,
) -> None:
    """Commit import session work, then update job progress (avoids SQLite 'database is locked')."""
    if not force and idx > 0 and idx % every != 0:
        return
    session.commit()
    jobs.update(job_id, **kwargs)  # type: ignore[arg-type]
