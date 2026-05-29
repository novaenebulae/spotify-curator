from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_playlists import Playlist, PlaylistTrack
from app.jobs.service import JobService
from app.library.job_progress import PROGRESS_UPDATE_EVERY, report_job_progress
from app.library.track_upsert import upsert_track_from_spotify_json
from app.spotify.client import SpotifyClient
from app.spotify.market_status import derive_playlist_item_null_reason


def _dt_parse(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None)


def _fetch_playlists_with_progress(
    *,
    job_id: str,
    jobs: JobService,
    client: SpotifyClient,
    limit: int = 50,
) -> list[dict]:
    offset = 0
    playlists: list[dict] = []
    total: int | None = None

    jobs.update(job_id, progress_current=0, progress_total=0, current_step="Fetching playlists…")

    while True:
        page = client.get_playlists_page(limit=limit, offset=offset)
        if total is None and page.total is not None:
            total = page.total
            jobs.update(job_id, progress_total=total)

        playlists.extend(page.items)
        fetched = len(playlists)
        step = f"Fetching {fetched}/{total}" if total is not None else f"Fetching {fetched}…"
        jobs.update(job_id, progress_current=fetched, current_step=step)

        if not page.next_url:
            break
        offset += limit

    jobs.update(
        job_id,
        progress_total=len(playlists),
        progress_current=0,
        current_step="Importing playlists…",
    )
    return playlists


def import_playlists(*, job_id: str, jobs: JobService, client: SpotifyClient) -> dict:
    playlists = _fetch_playlists_with_progress(job_id=job_id, jobs=jobs, client=client)

    engine = get_engine()
    now = datetime.now(tz=UTC).replace(tzinfo=None)

    playlist_count = 0
    item_count = 0
    unavailable_items = 0
    total = len(playlists)

    with Session(engine) as session:
        for idx, pl in enumerate(playlists, start=1):
            report_job_progress(
                session,
                jobs,
                job_id,
                idx=idx,
                force=idx == 1 or idx == total or idx % PROGRESS_UPDATE_EVERY == 0,
                progress_current=idx,
                progress_total=total,
                current_step=f"Importing playlist {idx}/{total}",
            )

            spotify_playlist_id = pl.get("id")
            if not spotify_playlist_id:
                continue

            playlist_row = session.execute(
                select(Playlist).where(Playlist.spotify_playlist_id == spotify_playlist_id)
            ).scalar_one_or_none()

            owner = (pl.get("owner") or {}).get("id") or ""
            playlist_name = pl.get("name") or ""

            if playlist_row is None:
                playlist_row = Playlist(
                    spotify_playlist_id=spotify_playlist_id,
                    spotify_uri=pl.get("uri") or "",
                    name=playlist_name,
                    description=pl.get("description") or "",
                    owner_spotify_user_id=owner,
                    is_public=pl.get("public"),
                    collaborative=pl.get("collaborative"),
                    spotify_snapshot_id=pl.get("snapshot_id") or "",
                    raw_json=json.dumps(pl),
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(playlist_row)
                session.flush()
                playlist_count += 1
            else:
                playlist_row.spotify_uri = pl.get("uri") or playlist_row.spotify_uri
                playlist_row.name = playlist_name or playlist_row.name
                playlist_row.description = pl.get("description") or ""
                playlist_row.owner_spotify_user_id = owner
                playlist_row.is_public = pl.get("public")
                playlist_row.collaborative = pl.get("collaborative")
                playlist_row.spotify_snapshot_id = pl.get("snapshot_id") or ""
                playlist_row.raw_json = json.dumps(pl)
                if playlist_row.first_seen_at is None:
                    playlist_row.first_seen_at = now
                playlist_row.last_seen_at = now

            session.execute(
                update(PlaylistTrack)
                .where(PlaylistTrack.spotify_playlist_id == spotify_playlist_id)
                .values(is_current=False)
            )

            items = client.iter_playlist_items(playlist_id=spotify_playlist_id, limit=100)
            for pos, it in enumerate(items):
                track = it.get("track")
                spotify_track_id = None
                is_local = False
                null_reason = derive_playlist_item_null_reason(it)

                if isinstance(track, dict):
                    is_local = bool(track.get("is_local"))
                    spotify_track_id = upsert_track_from_spotify_json(
                        session, track_json=track, now=now
                    )
                else:
                    unavailable_items += 1

                added_by = (it.get("added_by") or {}).get("id") or ""
                added_at = _dt_parse(it.get("added_at"))

                existing_item = session.execute(
                    select(PlaylistTrack).where(
                        PlaylistTrack.spotify_playlist_id == spotify_playlist_id,
                        PlaylistTrack.position == pos,
                    )
                ).scalar_one_or_none()

                if existing_item is None:
                    session.add(
                        PlaylistTrack(
                            spotify_playlist_id=spotify_playlist_id,
                            position=pos,
                            spotify_track_id=spotify_track_id,
                            added_at=added_at,
                            added_by_spotify_user_id=added_by,
                            is_current=True,
                            is_local=is_local,
                            null_reason=null_reason,
                            first_seen_at=now,
                            last_seen_at=now,
                            raw_json=json.dumps(it),
                        )
                    )
                else:
                    existing_item.spotify_track_id = spotify_track_id
                    existing_item.added_at = added_at
                    existing_item.added_by_spotify_user_id = added_by
                    existing_item.is_current = True
                    existing_item.is_local = is_local
                    existing_item.null_reason = null_reason
                    existing_item.last_seen_at = now
                    if existing_item.first_seen_at is None:
                        existing_item.first_seen_at = added_at or now
                    existing_item.raw_json = json.dumps(it)

                item_count += 1

        session.commit()

    jobs.update(
        job_id,
        progress_current=total,
        progress_total=total,
        current_step="Completed",
        result_json={
            "playlists": total,
            "items": item_count,
            "unavailable_items": unavailable_items,
        },
    )
    return {
        "playlists": total,
        "items": item_count,
        "unavailable_items": unavailable_items,
    }
