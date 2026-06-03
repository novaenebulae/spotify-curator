from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.repositories.generated_playlists import GeneratedPlaylistsRepository
from app.observability.errors import ApiError
from app.playlists.preview_service import PlaylistPreviewService
from app.playlists.rule_schemas import PlaylistRule
from app.playlists.rules_service import PlaylistRulesService

router = APIRouter(prefix="/generated-playlists", tags=["generated_playlists"])
_preview = PlaylistPreviewService()
_generated = GeneratedPlaylistsRepository()
_rules = PlaylistRulesService()


class PreviewRequest(BaseModel):
    rule_id: int | None = None
    rule: dict[str, Any] | None = None
    override: dict[str, Any] | None = None


@router.post("/preview")
def create_preview(body: PreviewRequest) -> dict:
    engine = get_engine()
    with Session(engine) as session:
        if body.rule_id is not None:
            row = _rules.get(session, body.rule_id)
            rule = PlaylistRule.model_validate(json.loads(row.rule_json))
            playlist_rule_id = row.id
        elif body.rule is not None:
            rule = PlaylistRule.model_validate(body.rule)
            playlist_rule_id = None
        else:
            raise ApiError(
                status_code=400,
                code="RULE_REQUIRED",
                message="rule_id or rule required",
            )
        return _preview.generate_preview(
            session,
            rule,
            playlist_rule_id=playlist_rule_id,
            override=body.override,
        )


@router.get("")
def list_generated() -> dict:
    engine = get_engine()
    with Session(engine) as session:
        rows = _generated.list_recent(session)
        return {
            "items": [
                {
                    "id": r.id,
                    "name": r.name,
                    "status": r.status,
                    "target_size": r.target_size,
                    "actual_size": r.actual_size,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        }


@router.get("/{generated_playlist_id}")
def get_generated(generated_playlist_id: int) -> dict:
    engine = get_engine()
    with Session(engine) as session:
        gp = _generated.get(session, generated_playlist_id)
        if gp is None:
            raise ApiError(
                status_code=404,
                code="GENERATED_PLAYLIST_NOT_FOUND",
                message="Generated playlist not found",
            )
        items = _generated.list_items(session, generated_playlist_id)
        return {
            "id": gp.id,
            "name": gp.name,
            "status": gp.status,
            "config": json.loads(gp.config_json),
            "summary": json.loads(gp.score_summary_json) if gp.score_summary_json else None,
            "warnings": json.loads(gp.warning_json) if gp.warning_json else [],
            "items": [
                {
                    "track_id": it.track_id,
                    "position": it.position,
                    "final_score": it.final_score,
                    "score_details": json.loads(it.score_details_json),
                    "selected_reason": it.selected_reason,
                }
                for it in items
            ],
        }
