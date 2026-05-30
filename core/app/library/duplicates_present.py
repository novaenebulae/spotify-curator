from __future__ import annotations

from typing import Any

REASON_LABELS: dict[str, str] = {
    "same_isrc": "Same ISRC",
    "same_title_primary_artist": "Same title and artist",
    "same_title_artist_similar_duration": "Same title, artist and close duration",
    "same_spotify_track_id": "Same Spotify track in multiple contexts",
}


def _fingerprint(track: dict[str, Any]) -> str:
    artists = ",".join(sorted(track.get("artist_names") or []))
    album = track.get("album_name") or ""
    return (
        f"{track.get('spotify_track_id') or ''}|"
        f"{track.get('title') or ''}|{artists}|{album}|{track.get('duration_ms') or 0}"
    )


def dedupe_tracks_for_display(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse rows by spotify_track_id then metadata fingerprint."""
    by_spotify: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for t in tracks:
        sp = t.get("spotify_track_id") or ""
        key = sp if sp else f"tid:{t.get('track_id')}"
        if key not in by_spotify:
            by_spotify[key] = {**t, "occurrence_count": 0, "member_track_ids": []}
            order.append(key)
        row = by_spotify[key]
        row["occurrence_count"] = int(row.get("occurrence_count", 0)) + 1
        tid = t.get("track_id")
        if tid is not None:
            row.setdefault("member_track_ids", []).append(tid)

    by_fingerprint: dict[str, dict[str, Any]] = {}
    fp_order: list[str] = []
    for key in order:
        row = by_spotify[key]
        fp = _fingerprint(row)
        if fp not in by_fingerprint:
            by_fingerprint[fp] = {
                **row,
                "occurrence_count": 0,
                "member_track_ids": [],
            }
            fp_order.append(fp)
        merged = by_fingerprint[fp]
        merged["occurrence_count"] = int(merged.get("occurrence_count", 0)) + int(
            row.get("occurrence_count", 1)
        )
        merged["member_track_ids"] = list(
            set(merged.get("member_track_ids", []) + row.get("member_track_ids", []))
        )
    return [by_fingerprint[fp] for fp in fp_order]


def present_duplicate_group(
    *,
    group_id: str,
    strategy: str,
    confidence: float,
    reason: str,
    raw_tracks: list[dict[str, Any]],
    contexts_by_spotify_id: dict[str, list[dict[str, str]]] | None = None,
) -> dict[str, Any]:
    occurrence_count = len(raw_tracks)
    unique_tracks = dedupe_tracks_for_display(raw_tracks)
    unique_track_count = len(unique_tracks)

    group_isrc = None
    for t in raw_tracks:
        if t.get("isrc"):
            group_isrc = t["isrc"]
            break

    if contexts_by_spotify_id:
        for ut in unique_tracks:
            sp = ut.get("spotify_track_id")
            if sp and sp in contexts_by_spotify_id:
                ut["contexts"] = contexts_by_spotify_id[sp]

    return {
        "group_id": group_id,
        "strategy": strategy,
        "confidence": confidence,
        "reason": reason,
        "reason_label": REASON_LABELS.get(reason, reason.replace("_", " ").title()),
        "occurrence_count": occurrence_count,
        "unique_track_count": unique_track_count,
        "is_repeated_occurrence": unique_track_count == 1 and occurrence_count > 1,
        "isrc": group_isrc,
        "tracks": unique_tracks,
    }
