from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_library import (
    Album,
    Artist,
    ExternalId,
    SpotifyAlbum,
    SpotifyArtist,
    SpotifyTrack,
    Track,
    TrackArtist,
)
from app.library.album_cover import apply_cover_to_album, extract_cover_from_images
from app.library.normalize import normalize_text
from app.spotify.market_status import derive_market_status


def upsert_track_from_spotify_json(
    session: Session,
    *,
    track_json: dict,
    now: datetime,
) -> str | None:
    spotify_track_id = track_json.get("id")
    if not spotify_track_id:
        return None

    title = track_json.get("name") or ""
    track_obj = Track(
        name=title,
        normalized_title=normalize_text(title),
        duration_ms=int(track_json.get("duration_ms") or 0),
        explicit=bool(track_json.get("explicit") or False),
        popularity=track_json.get("popularity"),
        preview_url=track_json.get("preview_url"),
        external_url=((track_json.get("external_urls") or {}).get("spotify")),
        raw_json=json.dumps(track_json),
        created_at=now,
        updated_at=now,
    )

    market_status = derive_market_status(track_json)
    restrictions = track_json.get("restrictions") or {}
    linked_from = (track_json.get("linked_from") or {}).get("id")

    album_id_fk: int | None = None
    album_json = track_json.get("album") or {}
    spotify_album_id = album_json.get("id")
    if spotify_album_id:
        album_name = album_json.get("name") or ""
        cover = extract_cover_from_images(album_json.get("images"))
        existing_sp_album = session.get(SpotifyAlbum, spotify_album_id)
        if existing_sp_album is None:
            album = Album(
                name=album_name,
                normalized_name=normalize_text(album_name),
                release_date=album_json.get("release_date"),
                raw_json=json.dumps(album_json),
                created_at=now,
                updated_at=now,
            )
            apply_cover_to_album(album, cover)
            session.add(album)
            session.flush()
            session.add(
                SpotifyAlbum(
                    spotify_album_id=spotify_album_id,
                    album_id=album.id,
                    spotify_uri=album_json.get("uri") or "",
                    raw_json=json.dumps(album_json),
                )
            )
            album_id_fk = album.id
        else:
            album_row = session.get(Album, existing_sp_album.album_id)
            if album_row is not None:
                album_row.name = album_name or album_row.name
                album_row.normalized_name = normalize_text(album_name)
                album_row.release_date = album_json.get("release_date")
                album_row.raw_json = json.dumps(album_json)
                album_row.updated_at = now
                apply_cover_to_album(album_row, cover)
            album_id_fk = existing_sp_album.album_id

    existing_sp_track = session.get(SpotifyTrack, spotify_track_id)
    if existing_sp_track is None:
        session.add(track_obj)
        session.flush()
        session.add(
            SpotifyTrack(
                spotify_track_id=spotify_track_id,
                track_id=track_obj.id,
                album_id=album_id_fk,
                spotify_uri=track_json.get("uri") or "",
                is_playable=track_json.get("is_playable"),
                available_markets_json=json.dumps(track_json.get("available_markets") or []),
                linked_from_spotify_track_id=linked_from,
                restrictions_json=json.dumps(restrictions),
                market_status=market_status,
                last_seen_at=now,
                raw_json=json.dumps(track_json),
            )
        )
    else:
        track_row = session.get(Track, existing_sp_track.track_id)
        if track_row is not None:
            track_row.name = track_obj.name
            track_row.normalized_title = track_obj.normalized_title
            track_row.duration_ms = track_obj.duration_ms
            track_row.explicit = track_obj.explicit
            track_row.popularity = track_obj.popularity
            track_row.preview_url = track_obj.preview_url
            track_row.external_url = track_obj.external_url
            track_row.raw_json = track_obj.raw_json
            track_row.updated_at = now

        existing_sp_track.spotify_uri = track_json.get("uri") or existing_sp_track.spotify_uri
        existing_sp_track.is_playable = track_json.get("is_playable")
        existing_sp_track.available_markets_json = json.dumps(
            track_json.get("available_markets") or []
        )
        existing_sp_track.linked_from_spotify_track_id = linked_from
        existing_sp_track.restrictions_json = json.dumps(restrictions)
        existing_sp_track.market_status = market_status
        existing_sp_track.last_seen_at = now
        existing_sp_track.raw_json = json.dumps(track_json)
        if album_id_fk is not None:
            existing_sp_track.album_id = album_id_fk

    sp_track_row = session.get(SpotifyTrack, spotify_track_id)
    track_id = sp_track_row.track_id if sp_track_row is not None else None
    if track_id:
        position = 0
        for art in track_json.get("artists") or []:
            if not isinstance(art, dict):
                continue
            spotify_artist_id = art.get("id")
            if not spotify_artist_id:
                continue
            artist_name = art.get("name") or ""
            existing_sp_artist = session.get(SpotifyArtist, spotify_artist_id)
            if existing_sp_artist is None:
                artist = Artist(
                    name=artist_name,
                    normalized_name=normalize_text(artist_name),
                    raw_json=json.dumps(art),
                    created_at=now,
                    updated_at=now,
                )
                session.add(artist)
                session.flush()
                session.add(
                    SpotifyArtist(
                        spotify_artist_id=spotify_artist_id,
                        artist_id=artist.id,
                        spotify_uri=art.get("uri") or "",
                        raw_json=json.dumps(art),
                    )
                )
                artist_id = artist.id
            else:
                artist_row = session.get(Artist, existing_sp_artist.artist_id)
                if artist_row is not None:
                    artist_row.name = artist_name or artist_row.name
                    artist_row.normalized_name = normalize_text(artist_name)
                    artist_row.raw_json = json.dumps(art)
                    artist_row.updated_at = now
                artist_id = existing_sp_artist.artist_id

            existing_link = session.execute(
                select(TrackArtist).where(
                    TrackArtist.track_id == track_id,
                    TrackArtist.artist_id == artist_id,
                )
            ).scalar_one_or_none()
            if existing_link is None:
                session.add(TrackArtist(track_id=track_id, artist_id=artist_id, position=position))
            else:
                existing_link.position = position
            position += 1

        external_ids = track_json.get("external_ids") or {}
        isrc = external_ids.get("isrc")
        if isrc:
            existing_isrc = session.execute(
                select(ExternalId).where(
                    ExternalId.track_id == track_id,
                    ExternalId.id_type == "isrc",
                )
            ).scalar_one_or_none()
            if existing_isrc is None:
                session.add(
                    ExternalId(
                        track_id=track_id,
                        id_type="isrc",
                        id_value=str(isrc),
                        source="spotify",
                        external_type="isrc",
                        confidence=1.0,
                    )
                )
            else:
                existing_isrc.id_value = str(isrc)
                existing_isrc.source = "spotify"
                existing_isrc.external_type = "isrc"
                existing_isrc.confidence = 1.0

    return spotify_track_id
