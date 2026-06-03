from __future__ import annotations

from app.playlists.explanations import ExclusionReason, TrackExclusion
from app.playlists.rule_schemas import PlaylistRule
from app.playlists.scoring import ScoreResult
from app.playlists.types import TrackFeatureView


def apply_diversity(
    rule: PlaylistRule,
    scored: list[ScoreResult],
    views: dict[int, TrackFeatureView],
) -> tuple[list[ScoreResult], list[TrackExclusion], list[str]]:
    warnings: list[str] = []
    if rule.constraints.cluster_diversity.enabled:
        warnings.append("CLUSTER_SOURCE_NOT_AVAILABLE_YET")

    active = [s for s in scored if not s.excluded]
    active.sort(key=lambda s: (-s.final_score, s.track_id))

    exclusions: list[TrackExclusion] = []
    selected: list[ScoreResult] = []
    artist_counts: dict[int, int] = {}
    album_counts: dict[int, int] = {}
    max_artist = rule.constraints.max_tracks_per_artist
    max_album = rule.constraints.max_tracks_per_album

    for sr in active:
        view = views.get(sr.track_id)
        if view is None:
            continue
        skip = False
        reasons: list[ExclusionReason] = []

        if max_artist is not None and view.artist_ids:
            aid = view.artist_ids[0]
            if artist_counts.get(aid, 0) >= max_artist:
                reasons.append(
                    ExclusionReason(
                        code="MAX_TRACKS_PER_ARTIST",
                        message=f"Artist {aid} limit {max_artist}",
                        field="artist_id",
                        value=aid,
                    )
                )
                skip = True

        if not skip and max_album is not None and view.album_id is not None:
            if album_counts.get(view.album_id, 0) >= max_album:
                reasons.append(
                    ExclusionReason(
                        code="MAX_TRACKS_PER_ALBUM",
                        message=f"Album {view.album_id} limit {max_album}",
                        field="album_id",
                        value=view.album_id,
                    )
                )
                skip = True

        if skip:
            exclusions.append(TrackExclusion(track_id=sr.track_id, reasons=reasons))
            continue

        selected.append(sr)
        if view.artist_ids:
            artist_counts[view.artist_ids[0]] = artist_counts.get(view.artist_ids[0], 0) + 1
        if view.album_id is not None:
            album_counts[view.album_id] = album_counts.get(view.album_id, 0) + 1

        if len(selected) >= rule.target_size:
            break

    if rule.constraints.avoid_same_artist_consecutive:
        selected = _spread_consecutive_artists(selected, views, exclusions)

    return selected, exclusions, warnings


def _spread_consecutive_artists(
    ordered: list[ScoreResult],
    views: dict[int, TrackFeatureView],
    exclusions: list[TrackExclusion],
) -> list[ScoreResult]:
    if len(ordered) < 2:
        return ordered
    result: list[ScoreResult] = []
    pool = list(ordered)
    while pool:
        placed = False
        for i, sr in enumerate(pool):
            view = views[sr.track_id]
            if not result:
                result.append(sr)
                pool.pop(i)
                placed = True
                break
            prev = views[result[-1].track_id]
            if view.artist_ids and prev.artist_ids and view.artist_ids[0] == prev.artist_ids[0]:
                continue
            result.append(sr)
            pool.pop(i)
            placed = True
            break
        if not placed:
            result.append(pool.pop(0))
    return result
