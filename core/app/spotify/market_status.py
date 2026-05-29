from __future__ import annotations

from typing import Any

STATUS_AVAILABLE = "available"
STATUS_UNAVAILABLE = "unavailable"
STATUS_MISSING = "missing"
STATUS_UNKNOWN = "unknown"


def derive_market_status(track_json: dict[str, Any] | None) -> str:
    if track_json is None:
        return STATUS_MISSING
    if not isinstance(track_json, dict):
        return STATUS_UNKNOWN

    restrictions = track_json.get("restrictions")
    if restrictions:
        return STATUS_UNAVAILABLE

    is_playable = track_json.get("is_playable")
    if is_playable is False:
        return STATUS_UNAVAILABLE

    if is_playable is True:
        return STATUS_AVAILABLE

    return STATUS_UNKNOWN


def derive_playlist_item_null_reason(item_json: dict[str, Any] | None) -> str | None:
    if item_json is None:
        return "unknown"
    track = item_json.get("track")
    if track is None:
        return "unavailable"
    if not isinstance(track, dict):
        return "unknown"
    if track.get("is_local"):
        return "local"
    if track.get("type") == "episode":
        return "episode"
    if not track.get("id"):
        return "unavailable"
    return None
