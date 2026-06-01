from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

_SPOTIFY_TRACK_RE = re.compile(r"open\.spotify\.com/track/([^/?#]+)")


def extract_batch_item_dicts(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("content"), list):
        return [item for item in payload["content"] if isinstance(item, dict)]
    if isinstance(payload.get("audioFeatures"), list):
        return [item for item in payload["audioFeatures"] if isinstance(item, dict)]
    has_features = payload.get("tempo") is not None or payload.get("acousticness") is not None
    if payload.get("id") or has_features:
        return [payload]
    return []


def _spotify_id_from_href(href: str | None) -> str | None:
    if not href:
        return None
    match = _SPOTIFY_TRACK_RE.search(href)
    if match:
        return match.group(1)
    parsed = urlparse(href)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[-2] == "track":
        return parts[-1]
    return None


def match_request_id(raw: dict[str, Any], requested_ids: set[str]) -> str | None:
    rb_id = raw.get("id")
    if rb_id is not None and str(rb_id) in requested_ids:
        return str(rb_id)
    isrc = raw.get("isrc")
    if isrc is not None and str(isrc) in requested_ids:
        return str(isrc)
    spotify_id = _spotify_id_from_href(raw.get("href"))
    if spotify_id and spotify_id in requested_ids:
        return spotify_id
    for req in requested_ids:
        if req and req in str(raw.get("href") or ""):
            return req
    return None


def identifiers_for_raw_item(raw: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    if raw.get("id") is not None:
        keys.add(str(raw["id"]))
    if raw.get("isrc") is not None:
        keys.add(str(raw["isrc"]))
    spotify_id = _spotify_id_from_href(raw.get("href"))
    if spotify_id:
        keys.add(spotify_id)
    return keys


def map_requested_ids_to_raw_items(
    raw_items: list[dict[str, Any]], requested_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Map each requested id to its API row when present in the batch response."""
    by_identifier: dict[str, dict[str, Any]] = {}
    for raw in raw_items:
        for key in identifiers_for_raw_item(raw):
            by_identifier[key] = raw

    mapped: dict[str, dict[str, Any]] = {}
    for req_id in requested_ids:
        raw = by_identifier.get(req_id)
        if raw is not None:
            mapped[req_id] = raw
    return mapped
