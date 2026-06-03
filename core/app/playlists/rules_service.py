from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.database.repositories.playlist_rules import PlaylistRulesRepository
from app.observability.errors import ApiError
from app.playlists.rule_validation import PlaylistRuleValidator, parse_rule_json


class PlaylistRulesService:
    def __init__(self) -> None:
        self._repo = PlaylistRulesRepository()
        self._validator = PlaylistRuleValidator()

    def validate(self, *, rule: dict | None = None, rule_yaml: str | None = None):
        return self._validator.validate(rule=rule, rule_yaml=rule_yaml)

    def create(
        self,
        session: Session,
        *,
        name: str,
        rule: dict,
        description: str | None = None,
        rule_yaml: str | None = None,
    ):
        result = self._validator.validate(rule=rule, rule_yaml=rule_yaml)
        if not result.valid:
            raise ApiError(
                status_code=400,
                code="RULE_VALIDATION_FAILED",
                message="Rule validation failed",
                details={"errors": [e.model_dump() for e in result.errors]},
            )
        assert result.normalized_rule is not None
        row = self._repo.create(
            session,
            name=name or result.normalized_rule.get("name", "Untitled"),
            rule_json=json.dumps(result.normalized_rule),
            description=description,
            rule_yaml=rule_yaml,
        )
        session.commit()
        return row

    def list_rules(self, session: Session, *, enabled_only: bool = True):
        return self._repo.list_all(session, enabled_only=enabled_only)

    def get(self, session: Session, rule_id: int):
        row = self._repo.get(session, rule_id)
        if row is None:
            raise ApiError(status_code=404, code="RULE_NOT_FOUND", message="Rule not found")
        return row

    def update(
        self,
        session: Session,
        rule_id: int,
        *,
        name: str | None = None,
        rule: dict | None = None,
        description: str | None = None,
        rule_yaml: str | None = None,
        enabled: bool | None = None,
    ):
        row = self.get(session, rule_id)
        rule_json = None
        if rule is not None:
            result = self._validator.validate(rule=rule, rule_yaml=rule_yaml)
            if not result.valid:
                raise ApiError(
                    status_code=400,
                    code="RULE_VALIDATION_FAILED",
                    message="Rule validation failed",
                    details={"errors": [e.model_dump() for e in result.errors]},
                )
            assert result.normalized_rule is not None
            rule_json = json.dumps(result.normalized_rule)
        updated = self._repo.update(
            session,
            row,
            name=name,
            rule_json=rule_json,
            rule_yaml=rule_yaml,
            description=description,
            enabled=enabled,
        )
        session.commit()
        return updated

    def delete(self, session: Session, rule_id: int):
        row = self.get(session, rule_id)
        self._repo.soft_delete(session, row)
        session.commit()
        return row

    @staticmethod
    def rule_as_dict(row) -> dict:
        return parse_rule_json(row.rule_json)
