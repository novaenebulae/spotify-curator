from __future__ import annotations

from app.reccobeats.parsing import (
    extract_batch_item_dicts,
    map_requested_ids_to_raw_items,
    match_request_id,
)
from tests.fixtures.reccobeats_responses import SAMPLE_FEATURES, SAMPLE_TRACK, SPOTIFY_TRACK_ID


def test_extract_batch_item_dicts_content() -> None:
    payload = {"content": [{**SAMPLE_TRACK, **SAMPLE_FEATURES}]}
    items = extract_batch_item_dicts(payload)
    assert len(items) == 1
    assert items[0]["id"] == SAMPLE_TRACK["id"]


def test_extract_batch_item_dicts_root_list() -> None:
    payload = [{**SAMPLE_TRACK, **SAMPLE_FEATURES}]
    items = extract_batch_item_dicts(payload)
    assert len(items) == 1


def test_extract_batch_item_dicts_single_object() -> None:
    payload = {**SAMPLE_TRACK, **SAMPLE_FEATURES}
    items = extract_batch_item_dicts(payload)
    assert len(items) == 1


def test_match_request_id_by_spotify_href() -> None:
    raw = {**SAMPLE_TRACK, "href": f"https://open.spotify.com/track/{SPOTIFY_TRACK_ID}"}
    assert match_request_id(raw, {SPOTIFY_TRACK_ID}) == SPOTIFY_TRACK_ID


def test_map_requested_ids_to_raw_items() -> None:
    raw_items = [{**SAMPLE_TRACK, **SAMPLE_FEATURES, "href": "https://open.spotify.com/track/sp_t1"}]
    mapped = map_requested_ids_to_raw_items(raw_items, ["sp_t1", "missing_id"])
    assert "sp_t1" in mapped
    assert "missing_id" not in mapped


def test_spotify_id_with_underscore_in_href() -> None:
    """Test fixture ids like sp_t1 must not be truncated at underscore."""
    raw_items = [{**SAMPLE_TRACK, **SAMPLE_FEATURES, "href": "https://open.spotify.com/track/sp_t1"}]
    mapped = map_requested_ids_to_raw_items(raw_items, ["sp_t1"])
    assert "sp_t1" in mapped


def test_map_partial_api_response() -> None:
    """ReccoBeats may return fewer rows than requested ids (real API behaviour)."""
    raw_items = [
        {
            **SAMPLE_TRACK,
            **SAMPLE_FEATURES,
            "href": "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh",
        }
    ]
    mapped = map_requested_ids_to_raw_items(
        raw_items, ["4iV5W9uYEdYUVa79Axb7Rh", "0k2pWBRz8QpDnK0eivd853"]
    )
    assert "4iV5W9uYEdYUVa79Axb7Rh" in mapped
    assert "0k2pWBRz8QpDnK0eivd853" not in mapped
