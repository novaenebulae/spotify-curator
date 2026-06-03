from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.playlists.presets import load_presets
from app.playlists.rule_schemas import PlaylistRuleValidateRequest, PlaylistRuleValidateResponse
from app.playlists.rules_service import PlaylistRulesService

router = APIRouter(prefix="/playlist-rules", tags=["playlist_rules"])
_service = PlaylistRulesService()


class PlaylistRuleCreateRequest(BaseModel):
    name: str
    rule: dict[str, Any]
    description: str | None = None
    rule_yaml: str | None = None


class PlaylistRuleUpdateRequest(BaseModel):
    name: str | None = None
    rule: dict[str, Any] | None = None
    description: str | None = None
    rule_yaml: str | None = None
    enabled: bool | None = None


class PlaylistRuleOut(BaseModel):
    id: int
    name: str
    description: str | None
    rule: dict[str, Any]
    version: int
    enabled: bool


@router.get("/presets")
def list_presets() -> dict:
    return {"presets": load_presets()}


@router.post("/validate", response_model=PlaylistRuleValidateResponse)
def validate_rule(body: PlaylistRuleValidateRequest) -> PlaylistRuleValidateResponse:
    return _service.validate(rule=body.rule, rule_yaml=body.rule_yaml)


@router.post("", response_model=PlaylistRuleOut)
def create_rule(body: PlaylistRuleCreateRequest) -> PlaylistRuleOut:
    engine = get_engine()
    with Session(engine) as session:
        row = _service.create(
            session,
            name=body.name,
            rule=body.rule,
            description=body.description,
            rule_yaml=body.rule_yaml,
        )
        return PlaylistRuleOut(
            id=row.id,
            name=row.name,
            description=row.description,
            rule=json.loads(row.rule_json),
            version=row.version,
            enabled=row.enabled,
        )


@router.get("")
def list_rules(enabled_only: bool = True) -> dict:
    engine = get_engine()
    with Session(engine) as session:
        rows = _service.list_rules(session, enabled_only=enabled_only)
        return {
            "items": [
                PlaylistRuleOut(
                    id=r.id,
                    name=r.name,
                    description=r.description,
                    rule=json.loads(r.rule_json),
                    version=r.version,
                    enabled=r.enabled,
                ).model_dump()
                for r in rows
            ]
        }


@router.get("/{rule_id}", response_model=PlaylistRuleOut)
def get_rule(rule_id: int) -> PlaylistRuleOut:
    engine = get_engine()
    with Session(engine) as session:
        row = _service.get(session, rule_id)
        return PlaylistRuleOut(
            id=row.id,
            name=row.name,
            description=row.description,
            rule=json.loads(row.rule_json),
            version=row.version,
            enabled=row.enabled,
        )


@router.put("/{rule_id}", response_model=PlaylistRuleOut)
def update_rule(rule_id: int, body: PlaylistRuleUpdateRequest) -> PlaylistRuleOut:
    engine = get_engine()
    with Session(engine) as session:
        row = _service.update(
            session,
            rule_id,
            name=body.name,
            rule=body.rule,
            description=body.description,
            rule_yaml=body.rule_yaml,
            enabled=body.enabled,
        )
        return PlaylistRuleOut(
            id=row.id,
            name=row.name,
            description=row.description,
            rule=json.loads(row.rule_json),
            version=row.version,
            enabled=row.enabled,
        )


@router.delete("/{rule_id}")
def delete_rule(rule_id: int) -> dict:
    engine = get_engine()
    with Session(engine) as session:
        _service.delete(session, rule_id)
    return {"ok": True, "enabled": False}
