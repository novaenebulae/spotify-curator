from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models_library_actions import LibraryAction


class LibraryActionsRepository:
    def create(
        self,
        session: Session,
        *,
        action_type: str,
        filter_json: dict,
        selected_track_ids: list[int],
        affected_count: int,
        dry_run: bool,
        result: dict,
        warnings: list[dict],
        created_by_context: str = "api",
    ) -> LibraryAction:
        now = datetime.utcnow()
        row = LibraryAction(
            action_type=action_type,
            status="previewed",
            filter_json=json.dumps(filter_json),
            selected_track_ids_json=json.dumps(selected_track_ids),
            affected_count=affected_count,
            dry_run=dry_run,
            spotify_applied=False,
            result_json=json.dumps(result),
            warning_json=json.dumps(warnings) if warnings else None,
            created_by_context=created_by_context,
            created_at=now,
            completed_at=now,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def list_actions(
        self,
        session: Session,
        *,
        action_type: str | None = None,
        dry_run: bool | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LibraryAction], int]:
        stmt = select(LibraryAction)
        if action_type:
            stmt = stmt.where(LibraryAction.action_type == action_type)
        if dry_run is not None:
            stmt = stmt.where(LibraryAction.dry_run == dry_run)
        if status:
            stmt = stmt.where(LibraryAction.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.execute(count_stmt).scalar_one()
        offset = (page - 1) * page_size
        rows = list(
            session.execute(
                stmt.order_by(LibraryAction.created_at.desc()).offset(offset).limit(page_size)
            )
            .scalars()
            .all()
        )
        return rows, total

    def get_by_id(self, session: Session, action_id: int) -> LibraryAction | None:
        return session.get(LibraryAction, action_id)
