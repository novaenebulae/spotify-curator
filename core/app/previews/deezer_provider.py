from __future__ import annotations

import logging

from app.audio.provider import TrackContext
from app.previews.deezer_client import DeezerClient, DeezerClientError
from app.previews.matching import is_isrc_exact_match, score_deezer_match, score_isrc_exact_match
from app.previews.schemas import DeezerTrackResult, PreviewCandidate
from app.settings.config import settings

_logger = logging.getLogger(__name__)

MATCH_STRATEGY_ISRC_EXACT = "isrc_exact"
MATCH_STRATEGY_METADATA_FUZZY = "metadata_fuzzy"
MATCH_STRATEGY_UNAVAILABLE = "unavailable"


class DeezerPreviewProvider:
    def __init__(self, client: DeezerClient | None = None) -> None:
        self._client = client or DeezerClient()

    def resolve_preview(self, track: TrackContext) -> PreviewCandidate:
        expected_s = track.duration_ms / 1000.0 if track.duration_ms else None

        if track.isrc:
            isrc_hit = self._client.get_track_by_isrc(track.isrc)
            if isrc_hit is None:
                _logger.debug("ISRC lookup returned no result for track %s", track.track_id)
            elif is_isrc_exact_match(track, isrc_hit) and isrc_hit.preview_url:
                return self._candidate_from_result(
                    track,
                    isrc_hit,
                    expected_s=expected_s,
                    match_strategy=MATCH_STRATEGY_ISRC_EXACT,
                    match_score=1.0,
                    match_confidence=1.0,
                )
            elif isrc_hit is not None and not isrc_hit.preview_url:
                _logger.debug(
                    "ISRC hit without preview for track %s, falling back to search",
                    track.track_id,
                )

        return self._resolve_fuzzy(track, expected_s=expected_s)

    def _resolve_fuzzy(self, track: TrackContext, *, expected_s: float | None) -> PreviewCandidate:
        query = f"{track.primary_artist} {track.title}".strip()
        try:
            results = self._client.search_track(query, limit=15)
        except DeezerClientError as exc:
            return self._unavailable(track, expected_s, str(exc))

        best: DeezerTrackResult | None = None
        best_score = -1.0
        best_conf = 0.0
        best_strategy = MATCH_STRATEGY_METADATA_FUZZY
        for cand in results:
            isrc_score, isrc_conf = score_isrc_exact_match(track, cand)
            if isrc_conf >= 1.0:
                return self._candidate_from_result(
                    track,
                    cand,
                    expected_s=expected_s,
                    match_strategy=MATCH_STRATEGY_ISRC_EXACT,
                    match_score=isrc_score,
                    match_confidence=isrc_conf,
                )
            score, conf = score_deezer_match(track, cand)
            if score > best_score:
                best_score = score
                best_conf = conf
                best = cand

        if best is None:
            return self._unavailable(track, expected_s, "No Deezer results")

        return self._candidate_from_result(
            track,
            best,
            expected_s=expected_s,
            match_strategy=best_strategy,
            match_score=best_score,
            match_confidence=best_conf,
        )

    def _candidate_from_result(
        self,
        track: TrackContext,
        result: DeezerTrackResult,
        *,
        expected_s: float | None,
        match_strategy: str,
        match_score: float,
        match_confidence: float,
    ) -> PreviewCandidate:
        delta = None
        if expected_s is not None and result.duration_seconds is not None:
            delta = abs(expected_s - result.duration_seconds)

        available = bool(result.preview_url) and match_confidence >= settings.deezer_preview_ui_min_confidence
        last_error: str | None = None
        if not result.preview_url:
            last_error = "isrc_no_preview" if match_strategy == MATCH_STRATEGY_ISRC_EXACT else "no_preview_url"
        elif not available:
            last_error = "below_confidence_threshold"

        return PreviewCandidate(
            provider="deezer",
            provider_track_id=result.id,
            provider_url=result.link,
            preview_url=result.preview_url,
            title=result.title,
            artist=result.artist_name,
            album=result.album_title,
            isrc=result.isrc or track.isrc,
            provider_duration_seconds=result.duration_seconds,
            expected_duration_seconds=expected_s,
            duration_delta_seconds=delta,
            match_score=match_score,
            match_confidence=match_confidence,
            match_strategy=match_strategy if available else MATCH_STRATEGY_UNAVAILABLE,
            is_available=available,
            last_error=last_error,
        )

    @staticmethod
    def _unavailable(track: TrackContext, expected_s: float | None, err: str) -> PreviewCandidate:
        return PreviewCandidate(
            provider="deezer",
            provider_track_id=None,
            provider_url=None,
            preview_url=None,
            title=track.title,
            artist=track.primary_artist,
            album=track.album,
            isrc=track.isrc,
            provider_duration_seconds=None,
            expected_duration_seconds=expected_s,
            duration_delta_seconds=None,
            match_score=0.0,
            match_confidence=0.0,
            match_strategy=MATCH_STRATEGY_UNAVAILABLE,
            is_available=False,
            last_error=err,
        )

    def meets_analysis_threshold(self, candidate: PreviewCandidate) -> bool:
        return (
            candidate.is_available
            and candidate.preview_url is not None
        )
