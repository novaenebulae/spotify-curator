from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_library import LikedTrack
from app.jobs.service import JobService
from app.library.job_progress import PROGRESS_UPDATE_EVERY, report_job_progress
from app.library.track_upsert import upsert_track_from_spotify_json
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
        session.execute(update(LikedTrack).values(is_current=False))

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

            spotify_track_id = upsert_track_from_spotify_json(
                session, track_json=track_json, now=now
            )
            if not spotify_track_id:
                continue

            existing_liked = session.get(LikedTrack, spotify_track_id)
            if existing_liked is None:
                session.add(
                    LikedTrack(
                        spotify_track_id=spotify_track_id,
                        added_at=added_at,
                        is_current=True,
                        first_seen_at=now,
                        last_seen_at=now,
                        raw_json=json.dumps(saved),
                    )
                )
                imported += 1
            else:
                existing_liked.added_at = added_at
                existing_liked.is_current = True
                existing_liked.last_seen_at = now
                if existing_liked.first_seen_at is None:
                    existing_liked.first_seen_at = added_at or now
                existing_liked.raw_json = json.dumps(saved)
                updated += 1

        session.commit()

    jobs.update(
        job_id,
        progress_current=total,
        progress_total=total,
        current_step="Completed",
        result_json={"imported": imported, "updated": updated, "total": total},
    )
    return {"imported": imported, "updated": updated, "total": total}
