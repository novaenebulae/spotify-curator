from __future__ import annotations

from app.playlists.explanations import ExclusionReason, TrackExclusion
from app.playlists.feature_registry import FeatureRegistry, get_feature_registry
from app.playlists.rule_schemas import FeatureFilterSpec, PlaylistRule
from app.playlists.types import FeatureValue, TrackFeatureView


def apply_strict_filters(
    rule: PlaylistRule,
    views: dict[int, TrackFeatureView],
    *,
    registry: FeatureRegistry | None = None,
) -> tuple[dict[int, TrackFeatureView], list[TrackExclusion], list[str]]:
    reg = registry or get_feature_registry()
    passed: dict[int, TrackFeatureView] = {}
    exclusions: list[TrackExclusion] = []
    warnings: list[str] = []

    for tid, view in views.items():
        exc = _filter_track(rule, view, reg)
        if exc:
            exclusions.append(exc)
        else:
            passed[tid] = view

    return passed, exclusions, warnings


def _filter_track(
    rule: PlaylistRule,
    view: TrackFeatureView,
    registry: FeatureRegistry,
) -> TrackExclusion | None:
    reasons: list[ExclusionReason] = []

    for fname, spec in rule.filters.features.items():
        canonical = registry.resolve_name(fname)
        if registry.is_future(canonical):
            continue
        fv = view.features.get(canonical) or view.features.get(fname)
        r = _check_feature_filter(fname, spec, fv, registry)
        if r:
            reasons.append(r)

    if rule.filters.availability_status:
        include = rule.filters.availability_status.get("include", [])
        if include and view.availability_status not in include:
            reasons.append(
                ExclusionReason(
                    code="TRACK_UNAVAILABLE",
                    message=f"availability {view.availability_status} not in {include}",
                    field="availability_status",
                    value=view.availability_status,
                    expected={"include": include},
                )
            )

    if rule.filters.market_status:
        include = rule.filters.market_status.get("include", [])
        if include and view.market_status not in include:
            reasons.append(
                ExclusionReason(
                    code="MARKET_UNAVAILABLE",
                    message=f"market {view.market_status} not in {include}",
                    field="market_status",
                    value=view.market_status,
                    expected={"include": include},
                )
            )

    for artist_id in rule.filters.exclude_artists:
        if artist_id in view.artist_ids:
            reasons.append(
                ExclusionReason(
                    code="ARTIST_EXCLUDED",
                    message=f"artist {artist_id} excluded",
                    field="artist_id",
                    value=artist_id,
                )
            )

    for album_id in rule.filters.exclude_albums:
        if view.album_id == album_id:
            reasons.append(
                ExclusionReason(
                    code="ALBUM_EXCLUDED",
                    message=f"album {album_id} excluded",
                    field="album_id",
                    value=album_id,
                )
            )

    if reasons:
        return TrackExclusion(track_id=view.track_id, reasons=reasons)
    return None


def _check_feature_filter(
    fname: str,
    spec: FeatureFilterSpec,
    fv: FeatureValue | None,
    registry: FeatureRegistry,
) -> ExclusionReason | None:
    canonical = registry.resolve_name(fname)
    if registry.is_future(canonical):
        return None

    if fv is None or fv.status in ("missing", "not_available_yet", "source_failed"):
        if spec.required:
            return ExclusionReason(
                code="FEATURE_MISSING" if fv is None else "FEATURE_NOT_AVAILABLE_YET",
                message=f"Feature {fname} missing",
                field=fname,
            )
        return None

    if fv.status == "low_confidence" and spec.required:
        return ExclusionReason(
            code="FEATURE_LOW_CONFIDENCE",
            message=f"Feature {fname} low confidence",
            field=fname,
            value=fv.confidence,
        )

    val = fv.value
    if val is None:
        if spec.required:
            return ExclusionReason(
                code="FEATURE_MISSING",
                message=f"Feature {fname} has no value",
                field=fname,
            )
        return None

    code_map = {
        "bpm": "BPM_OUT_OF_RANGE",
        "energy": "ENERGY_OUT_OF_RANGE",
        "valence": "VALENCE_OUT_OF_RANGE",
        "danceability": "DANCEABILITY_OUT_OF_RANGE",
        "loudness": "DANCEABILITY_OUT_OF_RANGE",
        "feature_confidence": "FEATURE_LOW_CONFIDENCE",
    }
    if spec.min is not None and float(val) < spec.min:
        return ExclusionReason(
            code=code_map.get(canonical, "BPM_OUT_OF_RANGE"),
            message=f"{fname} {val} below minimum {spec.min}",
            field=fname,
            value=val,
            expected={"min": spec.min, "max": spec.max},
        )
    if spec.max is not None and float(val) > spec.max:
        return ExclusionReason(
            code=code_map.get(canonical, "BPM_OUT_OF_RANGE"),
            message=f"{fname} {val} above maximum {spec.max}",
            field=fname,
            value=val,
            expected={"min": spec.min, "max": spec.max},
        )
    return None


def dedupe_isrc(
    views: dict[int, TrackFeatureView],
) -> tuple[dict[int, TrackFeatureView], list[TrackExclusion]]:
    seen: dict[str, int] = {}
    passed: dict[int, TrackFeatureView] = {}
    exclusions: list[TrackExclusion] = []
    for tid in sorted(views.keys()):
        view = views[tid]
        isrc = view.isrc
        if isrc and isrc in seen:
            exclusions.append(
                TrackExclusion(
                    track_id=tid,
                    reasons=[
                        ExclusionReason(
                            code="DUPLICATE_ISRC_EXCLUDED",
                            message=f"Duplicate ISRC {isrc}",
                            field="isrc",
                            value=isrc,
                        )
                    ],
                )
            )
            continue
        if isrc:
            seen[isrc] = tid
        passed[tid] = view
    return passed, exclusions
