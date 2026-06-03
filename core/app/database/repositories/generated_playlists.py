from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_playlists_engine import GeneratedPlaylist, GeneratedPlaylistItem


class GeneratedPlaylistsRepository:
    def create_preview(
        self,
        session: Session,
        *,
        name: str,
        config_json: str,
        target_size: int,
        playlist_rule_id: int | None,
        engine_version: str,
        score_summary_json: str | None,
        warning_json: str | None,
        items: list[dict],
    ) -> GeneratedPlaylist:
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        gp = GeneratedPlaylist(
            name=name,
            playlist_rule_id=playlist_rule_id,
            status="previewed",
            target_size=target_size,
            actual_size=len(items),
            engine_version=engine_version,
            score_summary_json=score_summary_json,
            config_json=config_json,
            warning_json=warning_json,
            created_at=now,
        )
        session.add(gp)
        session.flush()
        for idx, item in enumerate(items):
            session.add(
                GeneratedPlaylistItem(
                    generated_playlist_id=gp.id,
                    track_id=item["track_id"],
                    position=idx,
                    final_score=item["final_score"],
                    score_details_json=item.get("score_details_json", "{}"),
                    selected_reason=item.get("selected_reason"),
                    exclusion_details_json=item.get("exclusion_details_json"),
                    created_at=now,
                )
            )
        session.flush()
        return gp

    def get(self, session: Session, generated_id: int) -> GeneratedPlaylist | None:
        return session.get(GeneratedPlaylist, generated_id)

    def list_recent(self, session: Session, *, limit: int = 50) -> list[GeneratedPlaylist]:
        stmt = (
            select(GeneratedPlaylist)
            .order_by(GeneratedPlaylist.id.desc())
            .limit(limit)
        )
        return list(session.execute(stmt).scalars().all())

    def list_items(
        self, session: Session, generated_playlist_id: int
    ) -> list[GeneratedPlaylistItem]:
        stmt = (
            select(GeneratedPlaylistItem)
            .where(GeneratedPlaylistItem.generated_playlist_id == generated_playlist_id)
            .order_by(GeneratedPlaylistItem.position)
        )
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def summary_dict(
        *,
        candidate_count: int,
        selected_count: int,
        excluded_count: int,
        warnings: list[str],
    ) -> str:
        return json.dumps(
            {
                "candidate_count": candidate_count,
                "selected_count": selected_count,
                "excluded_count": excluded_count,
                "warnings": warnings,
            }
        )
