from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.audio.provider import AudioSourceCandidate, TrackContext
from app.settings.config import settings


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def text_match_score(track: TrackContext, title: str, channel: str) -> float:
    expected = _normalize(f"{track.title} {track.primary_artist}")
    candidate = _normalize(f"{title} {channel}")
    return SequenceMatcher(None, expected, candidate).ratio()


def score_candidate(
    track: TrackContext,
    *,
    title: str,
    channel: str,
    duration: float | None,
) -> tuple[float, float | None, str | None]:
    expected_s = track.duration_ms / 1000.0 if track.duration_ms > 0 else None
    delta = None
    rejected = None
    if duration is not None and expected_s is not None and expected_s > 0:
        delta = abs(duration - expected_s)
        if delta > settings.ytdlp_duration_tolerance_seconds:
            rejected = "duration_delta_too_high"
    text_score = text_match_score(track, title, channel)
    confidence = text_score
    if delta is not None and expected_s:
        duration_score = max(0.0, 1.0 - delta / max(expected_s, 1.0))
        confidence = 0.7 * text_score + 0.3 * duration_score
    return confidence, delta, rejected


def rank_candidates(
    track: TrackContext,
    entries: list[dict],
) -> list[AudioSourceCandidate]:
    results: list[AudioSourceCandidate] = []
    for entry in entries:
        url = entry.get("url") or entry.get("webpage_url") or ""
        if not url:
            vid = entry.get("id")
            if vid:
                url = f"https://www.youtube.com/watch?v={vid}"
        title = str(entry.get("title") or "")
        channel = str(entry.get("channel") or entry.get("uploader") or "")
        duration = entry.get("duration")
        duration_f = float(duration) if duration is not None else None
        confidence, delta, rejected = score_candidate(
            track, title=title, channel=channel, duration=duration_f
        )
        expected = track.duration_ms / 1000.0 if track.duration_ms > 0 else None
        results.append(
            AudioSourceCandidate(
                source="youtube",
                url=url,
                candidate_title=title,
                candidate_channel=channel,
                candidate_duration=duration_f,
                expected_duration=expected,
                duration_delta=delta,
                text_match_score=text_match_score(track, title, channel),
                confidence=confidence,
                selected=False,
                rejected_reason=rejected,
            )
        )
    results.sort(key=lambda c: c.confidence, reverse=True)
    viable = [c for c in results if c.rejected_reason is None]
    if viable:
        best = viable[0]
        results = [
            AudioSourceCandidate(
                source=best.source,
                url=best.url,
                candidate_title=best.candidate_title,
                candidate_channel=best.candidate_channel,
                candidate_duration=best.candidate_duration,
                expected_duration=best.expected_duration,
                duration_delta=best.duration_delta,
                text_match_score=best.text_match_score,
                confidence=best.confidence,
                selected=True,
                rejected_reason=None,
            ),
            *[
                AudioSourceCandidate(
                    source=c.source,
                    url=c.url,
                    candidate_title=c.candidate_title,
                    candidate_channel=c.candidate_channel,
                    candidate_duration=c.candidate_duration,
                    expected_duration=c.expected_duration,
                    duration_delta=c.duration_delta,
                    text_match_score=c.text_match_score,
                    confidence=c.confidence,
                    selected=False,
                    rejected_reason=c.rejected_reason,
                )
                for c in results
                if c.url != best.url
            ],
        ]
    return results
