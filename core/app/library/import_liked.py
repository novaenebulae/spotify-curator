from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_library import (
    Album,
    Artist,
    ExternalId,
    LikedTrack,
    SpotifyAlbum,
    SpotifyArtist,
    SpotifyTrack,
    Track,
    TrackArtist,
)
from app.jobs.service import JobService
from app.library.job_progress import PROGRESS_UPDATE_EVERY, report_job_progress
from app.spotify.client import SpotifyClient


def _dt_parse(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None)


def _fetch_saved_tracks_with_progress(
    *,
    job_id: str,
    jobs: JobService,
    client: SpotifyClient,
    limit: int = 50,
) -> list[dict]:
    offset = 0
    items: list[dict] = []
    total: int | None = None

    jobs.update(
        job_id,
        progress_current=0,
        progress_total=0,
        current_step="Fetching liked tracks…",
    )

    while True:
        page = client.get_saved_tracks_page(limit=limit, offset=offset)
        if total is None and page.total is not None:
            total = page.total
            jobs.update(job_id, progress_total=total)

        items.extend(page.items)
        fetched = len(items)
        step = f"Fetching {fetched}/{total}" if total is not None else f"Fetching {fetched}…"
        jobs.update(job_id, progress_current=fetched, current_step=step)

        if not page.next_url:
            break
        offset += limit

    jobs.update(job_id, progress_total=len(items), progress_current=0, current_step="Importing…")
    return items


def import_liked_tracks(*, job_id: str, jobs: JobService, client: SpotifyClient) -> dict:
    items = _fetch_saved_tracks_with_progress(job_id=job_id, jobs=jobs, client=client)

    engine = get_engine()
    imported = 0
    updated = 0
    total = len(items)

    now = datetime.now(tz=UTC).replace(tzinfo=None)

    with Session(engine) as session:
        for idx, saved in enumerate(items, start=1):
            report_job_progress(
                session,
                jobs,
                job_id,
                idx=idx,
                force=idx == 1 or idx == total or idx % PROGRESS_UPDATE_EVERY == 0,
                progress_current=idx,
                progress_total=total,
                current_step=f"Importing {idx}/{total}",
            )

            added_at = _dt_parse(saved.get("added_at"))
            track_json = saved.get("track")
            if not isinstance(track_json, dict):
                continue

            spotify_track_id = track_json.get("id")
            if not spotify_track_id:
                continue

            track_obj = Track(
                name=track_json.get("name") or "",
                duration_ms=int(track_json.get("duration_ms") or 0),
                explicit=bool(track_json.get("explicit") or False),
                popularity=track_json.get("popularity"),
                preview_url=track_json.get("preview_url"),
                external_url=((track_json.get("external_urls") or {}).get("spotify")),
                raw_json=json.dumps(track_json),
            )

            existing_sp_track = session.get(SpotifyTrack, spotify_track_id)
            if existing_sp_track is None:
                session.add(track_obj)
                session.flush()
                sp_track = SpotifyTrack(
                    spotify_track_id=spotify_track_id,
                    track_id=track_obj.id,
                    spotify_uri=track_json.get("uri") or "",
                    is_playable=track_json.get("is_playable"),
                    available_markets_json=json.dumps(track_json.get("available_markets") or []),
                    linked_from_spotify_track_id=((track_json.get("linked_from") or {}).get("id")),
                    restrictions_json=json.dumps(track_json.get("restrictions") or {}),
                    market_status="",
                    last_seen_at=now,
                    raw_json=json.dumps(track_json),
                )
                session.add(sp_track)
                imported += 1
            else:
                track_row = session.get(Track, existing_sp_track.track_id)
                if track_row is not None:
                    track_row.name = track_obj.name
                    track_row.duration_ms = track_obj.duration_ms
                    track_row.explicit = track_obj.explicit
                    track_row.popularity = track_obj.popularity
                    track_row.preview_url = track_obj.preview_url
                    track_row.external_url = track_obj.external_url
                    track_row.raw_json = track_obj.raw_json

                existing_sp_track.spotify_uri = (
                    track_json.get("uri") or existing_sp_track.spotify_uri
                )
                existing_sp_track.is_playable = track_json.get("is_playable")
                existing_sp_track.available_markets_json = json.dumps(
                    track_json.get("available_markets") or []
                )
                existing_sp_track.linked_from_spotify_track_id = (
                    (track_json.get("linked_from") or {}).get("id")
                )
                existing_sp_track.restrictions_json = json.dumps(
                    track_json.get("restrictions") or {}
                )
                existing_sp_track.last_seen_at = now
                existing_sp_track.raw_json = json.dumps(track_json)
                updated += 1

            album_json = track_json.get("album") or {}
            spotify_album_id = album_json.get("id")
            if spotify_album_id:
                existing_sp_album = session.get(SpotifyAlbum, spotify_album_id)
                if existing_sp_album is None:
                    album = Album(
                        name=album_json.get("name") or "",
                        release_date=album_json.get("release_date"),
                        raw_json=json.dumps(album_json),
                    )
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
                else:
                    album_row = session.get(Album, existing_sp_album.album_id)
                    if album_row is not None:
                        album_row.name = album_json.get("name") or album_row.name
                        album_row.release_date = album_json.get("release_date")
                        album_row.raw_json = json.dumps(album_json)

            artists_json = track_json.get("artists") or []
            sp_track_row = session.get(SpotifyTrack, spotify_track_id)
            track_id = sp_track_row.track_id if sp_track_row is not None else None
            if track_id:
                for art in artists_json:
                    if not isinstance(art, dict):
                        continue
                    spotify_artist_id = art.get("id")
                    if not spotify_artist_id:
                        continue
                    existing_sp_artist = session.get(SpotifyArtist, spotify_artist_id)
                    if existing_sp_artist is None:
                        artist = Artist(name=art.get("name") or "", raw_json=json.dumps(art))
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
                            artist_row.name = art.get("name") or artist_row.name
                            artist_row.raw_json = json.dumps(art)
                        artist_id = existing_sp_artist.artist_id

                    if (
                        session.get(
                            TrackArtist,
                            {"track_id": track_id, "artist_id": artist_id},
                        )
                        is None
                    ):
                        session.add(TrackArtist(track_id=track_id, artist_id=artist_id))

            external_ids = track_json.get("external_ids") or {}
            isrc = external_ids.get("isrc")
            if isrc and track_id:
                existing_isrc = session.execute(
                    select(ExternalId).where(
                        ExternalId.track_id == track_id,
                        ExternalId.id_type == "isrc",
                    )
                ).scalar_one_or_none()
                if existing_isrc is None:
                    session.add(ExternalId(track_id=track_id, id_type="isrc", id_value=str(isrc)))
                else:
                    existing_isrc.id_value = str(isrc)

            existing_liked = session.get(LikedTrack, spotify_track_id)
            if existing_liked is None:
                session.add(
                    LikedTrack(
                        spotify_track_id=spotify_track_id,
                        added_at=added_at,
                        raw_json=json.dumps(saved),
                    )
                )
            else:
                existing_liked.added_at = added_at
                existing_liked.raw_json = json.dumps(saved)

        session.commit()

    jobs.update(
        job_id,
        progress_current=total,
        progress_total=total,
        current_step="Completed",
        result_json={"imported": imported, "updated": updated, "total": total},
    )
    return {"imported": imported, "updated": updated, "total": total}
