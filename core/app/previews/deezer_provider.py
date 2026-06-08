from __future__ import annotations

import logging

from app.audio.provider import TrackContext
from app.previews.deezer_client import DeezerClient, DeezerClientError
from app.previews.matching import score_deezer_match
from app.previews.schemas import DeezerTrackResult, PreviewCandidate
from app.settings.config import settings

_logger = logging.getLogger(__name__)


class DeezerPreviewProvider:
    def __init__(self, client: DeezerClient | None = None) -> None:
        self._client = client or DeezerClient()

    def resolve_preview(self, track: TrackContext) -> PreviewCandidate:
        query = f"{track.primary_artist} {track.title}".strip()
        expected_s = track.duration_ms / 1000.0 if track.duration_ms else None
        try:
            results = self._client.search_track(query, limit=15)
        except DeezerClientError as exc:
            return self._unavailable(track, expected_s, str(exc))

        best: DeezerTrackResult | None = None
        best_score = -1.0
        best_conf = 0.0
        for cand in results:
            score, conf = score_deezer_match(track, cand)
            if score > best_score:
                best_score = score
                best_conf = conf
                best = cand

        if best is None:
            return self._unavailable(track, expected_s, "No Deezer results")

        delta = None
        if expected_s is not None and best.duration_seconds is not None:
            delta = abs(expected_s - best.duration_seconds)

        available = bool(best.preview_url) and best_conf >= settings.deezer_preview_ui_min_confidence
        return PreviewCandidate(
            provider="deezer",
            provider_track_id=best.id,
            provider_url=best.link,
            preview_url=best.preview_url,
            title=best.title,
            artist=best.artist_name,
            album=best.album_title,
            isrc=best.isrc or track.isrc,
            provider_duration_seconds=best.duration_seconds,
            expected_duration_seconds=expected_s,
            duration_delta_seconds=delta,
            match_score=best_score,
            match_confidence=best_conf,
            is_available=available,
            last_error=None if available else "Below confidence threshold or no preview URL",
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
            is_available=False,
            last_error=err,
        )

    def meets_analysis_threshold(self, candidate: PreviewCandidate) -> bool:
        return (
            candidate.is_available
            and candidate.preview_url is not None
        )
