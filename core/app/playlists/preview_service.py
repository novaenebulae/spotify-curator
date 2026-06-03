from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.database.repositories.generated_playlists import GeneratedPlaylistsRepository
from app.playlists.candidates import select_candidate_track_ids
from app.playlists.diversity import apply_diversity
from app.playlists.feature_registry import get_feature_registry
from app.playlists.feature_resolver import FeatureResolver
from app.playlists.filters import apply_strict_filters, dedupe_isrc
from app.playlists.ordering import apply_ordering
from app.playlists.rule_schemas import PlaylistRule
from app.playlists.rule_validation import PlaylistRuleValidator
from app.playlists.scoring import score_details_json, score_tracks


class PlaylistPreviewService:
    def __init__(self) -> None:
        self._validator = PlaylistRuleValidator()
        self._resolver = FeatureResolver()
        self._generated = GeneratedPlaylistsRepository()
        self._registry = get_feature_registry()

    def generate_preview(
        self,
        session: Session,
        rule: PlaylistRule,
        *,
        playlist_rule_id: int | None = None,
        override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if override:
            merged = rule.model_dump()
            merged.update(override)
            rule = PlaylistRule.model_validate(merged)

        candidate_ids, src_warnings = select_candidate_track_ids(session, rule)
        views_map = self._resolver.load_views(session, candidate_ids)

        if rule.constraints.avoid_duplicate_isrc:
            views_map, isrc_excl = dedupe_isrc(views_map)
        else:
            isrc_excl = []

        passed, filter_excl, _ = apply_strict_filters(rule, views_map)
        scored, score_warnings = score_tracks(rule, passed)
        scored_active = [s for s in scored if not s.excluded]
        selected, div_excl, div_warnings = apply_diversity(rule, scored_active, passed)
        ordered = apply_ordering(rule, selected, passed)

        all_warnings = list(
            dict.fromkeys(
                [w.code for w in src_warnings]
                + list(score_warnings)
                + list(div_warnings)
            )
        )

        exclusions = [e.to_dict() for e in filter_excl + isrc_excl + div_excl]
        for s in scored:
            if s.excluded:
                exclusions.append(
                    {
                        "track_id": s.track_id,
                        "excluded": True,
                        "reasons": [
                            {
                                "code": s.exclusion_code or "SCORE_NOT_COMPUTABLE",
                                "message": "Score not computable",
                            }
                        ],
                    }
                )

        items = []
        for pos, sr in enumerate(ordered):
            view = passed[sr.track_id]
            items.append(
                {
                    "track_id": sr.track_id,
                    "position": pos,
                    "final_score": sr.final_score,
                    "score_details_json": score_details_json(sr),
                    "selected_reason": "scored_and_selected",
                    "title": view.title,
                    "artist_names": view.artist_names,
                    "spotify_track_id": view.spotify_track_id,
                }
            )

        config_json = json.dumps(rule.model_dump_normalized())
        summary = self._generated.summary_dict(
            candidate_count=len(candidate_ids),
            selected_count=len(items),
            excluded_count=len(exclusions),
            warnings=all_warnings,
        )

        gp = self._generated.create_preview(
            session,
            name=rule.name,
            config_json=config_json,
            target_size=rule.target_size,
            playlist_rule_id=playlist_rule_id,
            engine_version=self._registry.ENGINE_VERSION,
            score_summary_json=summary,
            warning_json=json.dumps(all_warnings) if all_warnings else None,
            items=[
                {
                    "track_id": it["track_id"],
                    "final_score": it["final_score"],
                    "score_details_json": it["score_details_json"],
                    "selected_reason": it["selected_reason"],
                }
                for it in items
            ],
        )
        session.commit()

        return {
            "generated_playlist_id": gp.id,
            "items": items,
            "exclusions": exclusions,
            "summary": json.loads(summary),
            "warnings": all_warnings,
            "dry_run": True,
        }
