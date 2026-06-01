from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audio.provider import TrackContext
from app.database.models_library import Artist, SpotifyTrack, Track, TrackArtist
from app.observability.errors import ApiError


def load_track_context(session: Session, track_id: int) -> TrackContext:
    track = session.get(Track, track_id)
    if track is None:
        raise ApiError(code="NOT_FOUND", message="Track not found.", status_code=404)
    artist_name = session.execute(
        select(Artist.name)
        .join(TrackArtist, TrackArtist.artist_id == Artist.id)
        .where(TrackArtist.track_id == track_id, TrackArtist.position == 0)
        .limit(1)
    ).scalar_one_or_none()
    if not artist_name:
        artist_name = session.execute(
            select(Artist.name)
            .join(TrackArtist, TrackArtist.artist_id == Artist.id)
            .where(TrackArtist.track_id == track_id)
            .limit(1)
        ).scalar_one_or_none()
    album = None
    sp = session.execute(
        select(SpotifyTrack).where(SpotifyTrack.track_id == track_id)
    ).scalar_one_or_none()
    if sp and sp.album_id:
        from app.database.models_library import Album

        album_row = session.get(Album, sp.album_id) if sp.album_id else None
        album = album_row.name if album_row else None
    isrc = None
    from app.database.models_library import ExternalId

    isrc_row = session.execute(
        select(ExternalId.id_value).where(
            ExternalId.track_id == track_id,
            ExternalId.id_type == "isrc",
        )
    ).scalar_one_or_none()
    if isrc_row:
        isrc = str(isrc_row)
    return TrackContext(
        track_id=track_id,
        title=track.name,
        primary_artist=artist_name or "Unknown",
        album=album,
        duration_ms=int(track.duration_ms or 0),
        isrc=isrc,
    )
