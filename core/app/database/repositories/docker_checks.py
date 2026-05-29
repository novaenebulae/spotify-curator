from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_runtime import DockerRuntimeCheck


class DockerChecksRepository:
    def list_recent(self, session: Session, *, limit: int = 50) -> list[DockerRuntimeCheck]:
        return list(
            session.execute(
                select(DockerRuntimeCheck)
                .order_by(DockerRuntimeCheck.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def add(self, session: Session, row: DockerRuntimeCheck) -> DockerRuntimeCheck:
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
