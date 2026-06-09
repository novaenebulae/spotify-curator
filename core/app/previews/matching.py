from __future__ import annotations

import re
import unicodedata

from app.audio.provider import TrackContext
from app.previews.schemas import DeezerTrackResult

_PENALTY_PATTERNS = (
    (re.compile(r"\blive\b", re.I), 0.25),
    (re.compile(r"\bremix\b", re.I), 0.15),
    (re.compile(r"\bkaraoke\b", re.I), 0.40),
    (re.compile(r"\binstrumental\b", re.I), 0.20),
    (re.compile(r"\bacoustic\b", re.I), 0.05),
    (re.compile(r"\bcover\b", re.I), 0.10),
)


def normalize_text(value: str) -> str:
    nf = unicodedata.normalize("NFKD", value.lower())
    ascii_only = "".join(c for c in nf if not unicodedata.combining(c))
    ascii_only = re.sub(r"[^\w\s]", " ", ascii_only)
    return re.sub(r"\s+", " ", ascii_only).strip()


def token_overlap(a: str, b: str) -> float:
    ta = set(normalize_text(a).split())
    tb = set(normalize_text(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def duration_score(expected_s: float | None, actual_s: float | None) -> float:
    if expected_s is None or actual_s is None or expected_s <= 0:
        return 0.5
    delta = abs(expected_s - actual_s)
    if delta <= 3:
        return 1.0
    if delta <= 10:
        return 0.85
    if delta <= 30:
        return 0.6
    return max(0.0, 1.0 - delta / expected_s)


def penalty_for_title(title: str) -> float:
    total = 0.0
    for pattern, pen in _PENALTY_PATTERNS:
        if pattern.search(title):
            total += pen
    return min(total, 0.6)


def is_isrc_exact_match(track: TrackContext, candidate: DeezerTrackResult) -> bool:
    if not track.isrc or not candidate.isrc:
        return False
    return track.isrc.strip().upper() == candidate.isrc.strip().upper()


def score_isrc_exact_match(track: TrackContext, candidate: DeezerTrackResult) -> tuple[float, float]:
    if is_isrc_exact_match(track, candidate) and candidate.preview_url:
        return 1.0, 1.0
    return 0.0, 0.0


def score_deezer_match(track: TrackContext, candidate: DeezerTrackResult) -> tuple[float, float]:
    """Return (match_score 0-1, match_confidence 0-1)."""
    isrc_score, isrc_conf = score_isrc_exact_match(track, candidate)
    if isrc_conf >= 1.0:
        return isrc_score, isrc_conf

    title_s = token_overlap(track.title, candidate.title)
    artist_s = token_overlap(track.primary_artist, candidate.artist_name)
    expected_s = track.duration_ms / 1000.0 if track.duration_ms else None
    dur_s = duration_score(expected_s, candidate.duration_seconds)

    isrc_bonus = 0.35 if is_isrc_exact_match(track, candidate) else 0.0

    base = 0.45 * title_s + 0.35 * artist_s + 0.20 * dur_s + isrc_bonus
    pen = penalty_for_title(candidate.title)
    score = max(0.0, min(1.0, base - pen))

    if not candidate.preview_url:
        confidence = 0.0
    else:
        confidence = score
        if title_s < 0.3 or artist_s < 0.3:
            confidence *= 0.5

    return round(score, 4), round(confidence, 4)
