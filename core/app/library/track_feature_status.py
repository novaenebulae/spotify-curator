from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_advanced_features import TrackAdvancedFeature
from app.database.models_features import AudioFeature
from app.database.models_previews import TrackPreview
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.settings.config import settings

FeatureStatus = str  # success | partial | failed | not_found | missing


def _local_analysis_status(ess_st: FeatureStatus, has_tf_success: bool) -> FeatureStatus:
    if ess_st in ("failed",):
        return "failed"
    if ess_st in ("success", "partial") and has_tf_success:
        return "success"
    if ess_st in ("success", "partial") or has_tf_success:
        return "partial"
    if ess_st == "missing" and not has_tf_success:
        return "missing"
    return "missing"


def batch_feature_status_for_tracks(
    session: Session, track_ids: list[int]
) -> dict[int, dict[str, FeatureStatus | bool]]:
    if not track_ids:
        return {}

    sources = FeatureSourcesRepository()
    rb = sources.get_by_name(session, "reccobeats")
    ess = sources.get_by_name(session, "essentia_lowlevel")

    rb_by_track: dict[int, str] = {}
    ess_by_track: dict[int, str] = {}

    if rb is not None:
        rows = session.execute(
            select(AudioFeature.track_id, AudioFeature.status).where(
                AudioFeature.track_id.in_(track_ids),
                AudioFeature.feature_source_id == rb.id,
                AudioFeature.is_active.is_(True),
            )
        ).all()
        rb_by_track = {int(tid): str(st) for tid, st in rows}

    if ess is not None:
        rows = session.execute(
            select(AudioFeature.track_id, AudioFeature.status).where(
                AudioFeature.track_id.in_(track_ids),
                AudioFeature.feature_source_id == ess.id,
                AudioFeature.is_active.is_(True),
            )
        ).all()
        ess_by_track = {int(tid): str(st) for tid, st in rows}

    tf_success_tracks: set[int] = set()
    tf_rows = session.execute(
        select(TrackAdvancedFeature.track_id)
        .where(
            TrackAdvancedFeature.track_id.in_(track_ids),
            TrackAdvancedFeature.status.in_(("success", "partial")),
            TrackAdvancedFeature.value_float.is_not(None),
        )
        .group_by(TrackAdvancedFeature.track_id)
    ).all()
    tf_success_tracks = {int(r[0]) for r in tf_rows}

    preview_rows = session.execute(
        select(TrackPreview).where(
            TrackPreview.track_id.in_(track_ids),
            TrackPreview.provider == "deezer",
        )
    ).scalars().all()
    preview_by_track = {int(r.track_id): r for r in preview_rows}

    out: dict[int, dict[str, FeatureStatus | bool]] = {}
    ui_min = settings.deezer_preview_ui_min_confidence
    for tid in track_ids:
        rb_st: FeatureStatus = rb_by_track.get(tid, "missing")  # type: ignore[assignment]
        ess_st: FeatureStatus = ess_by_track.get(tid, "missing")  # type: ignore[assignment]
        has_tf = tid in tf_success_tracks
        local_st = _local_analysis_status(ess_st, has_tf)
        prev = preview_by_track.get(tid)
        preview_ok = False
        if prev is not None and prev.is_available and prev.preview_url:
            conf = float(prev.match_confidence or 0.0)
            preview_ok = conf >= ui_min
        out[tid] = {
            "reccobeats_status": rb_st,
            "essentia_status": ess_st,
            "local_analysis_status": local_st,
            "preview_available": preview_ok,
        }
    return out
