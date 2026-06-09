from __future__ import annotations

from typing import Any, Protocol

from app.settings.config import settings

ANALYSIS_DEEZER_ONLY = "deezer_only"
ANALYSIS_DEEZER_PLUS_YT_2 = "deezer_plus_youtube_2_segments"

VERDICT_OK = "ok"
VERDICT_MISMATCH = "mismatch"
VERDICT_ISRC_UNRESOLVABLE = "isrc_unresolvable"
VERDICT_NO_SPOTIFY_ISRC = "no_spotify_isrc"
VERDICT_LOW_CONFIDENCE_FUZZY = "low_confidence_fuzzy"

DEEZER_ANALYSIS_DECISIONS = frozenset({ANALYSIS_DEEZER_ONLY, ANALYSIS_DEEZER_PLUS_YT_2})
REMEDIATION_VERDICTS = frozenset({VERDICT_MISMATCH, VERDICT_LOW_CONFIDENCE_FUZZY})


class _PreviewLike(Protocol):
    provider_track_id: str | None
    match_strategy: str | None
    match_confidence: float | None


class _IsrcHitLike(Protocol):
    id: str


def classify_deezer_audit_verdict(
    *,
    preview: _PreviewLike | None,
    isrc_hit: _IsrcHitLike | None,
    stored_confidence: float | None,
) -> tuple[str, str | None]:
    if isrc_hit is None:
        return VERDICT_ISRC_UNRESOLVABLE, None

    stored_id = preview.provider_track_id if preview else None
    if stored_id and stored_id != isrc_hit.id:
        return VERDICT_MISMATCH, f"stored={stored_id} isrc_canonical={isrc_hit.id}"

    if preview and preview.match_strategy in (None, "") and stored_confidence is not None:
        if stored_confidence < settings.deezer_preview_ui_min_confidence:
            return VERDICT_LOW_CONFIDENCE_FUZZY, f"confidence={stored_confidence}"

    return VERDICT_OK, None


def analysis_decision_from_json(result_json: str | None) -> str | None:
    import json

    if not result_json:
        return None
    try:
        data = json.loads(result_json)
    except json.JSONDecodeError:
        return None
    decision = data.get("analysis_decision")
    return str(decision) if decision else None
