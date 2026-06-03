from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_playlists_engine import PlaylistRule


class PlaylistRulesRepository:
    def create(
        self,
        session: Session,
        *,
        name: str,
        rule_json: str,
        description: str | None = None,
        rule_yaml: str | None = None,
        enabled: bool = True,
    ) -> PlaylistRule:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        row = PlaylistRule(
            name=name,
            description=description,
            rule_json=rule_json,
            rule_yaml=rule_yaml,
            version=1,
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        return row

    def get(self, session: Session, rule_id: int) -> PlaylistRule | None:
        return session.get(PlaylistRule, rule_id)

    def list_all(
        self,
        session: Session,
        *,
        enabled_only: bool = True,
    ) -> list[PlaylistRule]:
        stmt = select(PlaylistRule).order_by(PlaylistRule.name)
        if enabled_only:
            stmt = stmt.where(PlaylistRule.enabled.is_(True))
        return list(session.execute(stmt).scalars().all())

    def update(
        self,
        session: Session,
        row: PlaylistRule,
        *,
        name: str | None = None,
        rule_json: str | None = None,
        rule_yaml: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
    ) -> PlaylistRule:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        if name is not None:
            row.name = name
        if rule_json is not None:
            row.rule_json = rule_json
            row.version += 1
        if rule_yaml is not None:
            row.rule_yaml = rule_yaml
        if description is not None:
            row.description = description
        if enabled is not None:
            row.enabled = enabled
        row.updated_at = now
        session.flush()
        return row

    def soft_delete(self, session: Session, row: PlaylistRule) -> PlaylistRule:
        return self.update(session, row, enabled=False)
