from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_library import ExternalId, SpotifyTrack
from app.reccobeats.schemas import (
    ReccoBeatsBatchEntry,
    ReccoBeatsBatchResult,
    ReccoBeatsFetchResult,
    ReccoBeatsTrackMeta,
)


@dataclass(frozen=True)
class TrackEnrichContext:
    track_id: int
    spotify_track_id: str | None
    isrc: str | None
    reccobeats_id: str | None


def load_enrich_contexts(session: Session, track_ids: list[int]) -> list[TrackEnrichContext]:
    if not track_ids:
        return []

    spotify_rows = session.execute(
        select(SpotifyTrack.track_id, SpotifyTrack.spotify_track_id).where(
            SpotifyTrack.track_id.in_(track_ids)
        )
    ).all()
    spotify_by_track = {int(row[0]): row[1] for row in spotify_rows}

    ext_rows = session.execute(
        select(ExternalId.track_id, ExternalId.id_type, ExternalId.id_value).where(
            ExternalId.track_id.in_(track_ids),
            ExternalId.id_type.in_(("isrc", "reccobeats_id")),
        )
    ).all()
    isrc_by_track: dict[int, str] = {}
    rb_by_track: dict[int, str] = {}
    for track_id, id_type, id_value in ext_rows:
        tid = int(track_id)
        if id_type == "isrc":
            isrc_by_track[tid] = id_value
        elif id_type == "reccobeats_id":
            rb_by_track[tid] = id_value

    contexts: list[TrackEnrichContext] = []
    for track_id in track_ids:
        contexts.append(
            TrackEnrichContext(
                track_id=track_id,
                spotify_track_id=spotify_by_track.get(track_id),
                isrc=isrc_by_track.get(track_id),
                reccobeats_id=rb_by_track.get(track_id),
            )
        )
    return contexts


def request_id_for(ctx: TrackEnrichContext, *, force_refresh: bool) -> str | None:
    if ctx.spotify_track_id:
        return ctx.spotify_track_id
    if ctx.isrc:
        return ctx.isrc
    if ctx.reccobeats_id and not force_refresh:
        return ctx.reccobeats_id
    return None


def chunk_contexts(
    contexts: list[tuple[TrackEnrichContext, str]], chunk_size: int
) -> list[list[tuple[TrackEnrichContext, str]]]:
    if chunk_size < 1:
        chunk_size = 1
    chunks: list[list[tuple[TrackEnrichContext, str]]] = []
    for i in range(0, len(contexts), chunk_size):
        chunks.append(contexts[i : i + chunk_size])
    return chunks


def index_batch_entries(entries: list[ReccoBeatsBatchEntry]) -> dict[str, ReccoBeatsBatchEntry]:
    index: dict[str, ReccoBeatsBatchEntry] = {}
    for entry in entries:
        index[entry.request_id] = entry
        if entry.track:
            if entry.track.id:
                index[entry.track.id] = entry
            if entry.track.spotify_track_id:
                index[entry.track.spotify_track_id] = entry
            if entry.track.isrc:
                index[entry.track.isrc] = entry
    return index


def batch_entry_to_fetch_result(
    entry: ReccoBeatsBatchEntry | None,
    ctx: TrackEnrichContext,
    *,
    batch_result: ReccoBeatsBatchResult | None = None,
) -> ReccoBeatsFetchResult:
    if entry is None or entry.features is None:
        return ReccoBeatsFetchResult(
            track=None,
            features=None,
            track_raw=entry.raw if entry else {},
            features_raw={},
            track_status_code=batch_result.status_code if batch_result else None,
            features_status_code=entry.features_status_code if entry else None,
        )

    track_meta = entry.track
    if track_meta is None:
        track_meta = ReccoBeatsTrackMeta(
            id=entry.request_id,
            track_title="",
            artists=[],
            duration_ms=entry.features.duration_ms,
            isrc=ctx.isrc,
            href=None,
            spotify_track_id=ctx.spotify_track_id,
        )
    elif track_meta.spotify_track_id is None and ctx.spotify_track_id:
        track_meta = ReccoBeatsTrackMeta(
            id=track_meta.id,
            track_title=track_meta.track_title,
            artists=track_meta.artists,
            duration_ms=track_meta.duration_ms or entry.features.duration_ms,
            isrc=track_meta.isrc or ctx.isrc,
            href=track_meta.href,
            spotify_track_id=ctx.spotify_track_id,
        )

    return ReccoBeatsFetchResult(
        track=track_meta,
        features=entry.features,
        track_raw=entry.raw,
        features_raw=entry.raw,
        track_status_code=batch_result.status_code if batch_result else None,
        features_status_code=entry.features_status_code,
    )


def build_batch_raw_payload_json(
    fetch_result: ReccoBeatsFetchResult,
    *,
    batch_result: ReccoBeatsBatchResult,
    entry: ReccoBeatsBatchEntry,
) -> str:
    import json

    payload = {
        "batch": batch_result.raw_payload,
        "entry": entry.raw,
        "track": fetch_result.track_raw,
        "features": fetch_result.features_raw,
        "track_status_code": fetch_result.track_status_code,
        "features_status_code": fetch_result.features_status_code,
    }
    return json.dumps(payload)


def entry_has_features(entry: ReccoBeatsBatchEntry | None) -> bool:
    if entry is None or entry.features is None:
        return False
    f = entry.features
    return any(
        v is not None
        for v in (
            f.acousticness,
            f.danceability,
            f.energy,
            f.tempo,
            f.valence,
        )
    )
