from __future__ import annotations

from fastapi import APIRouter

from app.jobs.service import JobService
from app.library.import_liked import import_liked_tracks
from app.library.import_playlists import import_playlists
from app.spotify.client import SpotifyClient, SpotifyError
from app.spotify.token_store import SpotifyTokenStore

router = APIRouter(prefix="/spotify/import")
_jobs = JobService()


@router.post("/liked-tracks")
def import_liked_tracks_job() -> dict:
    job_id = _jobs.create("spotify_import_liked_tracks")

    def _run() -> dict:
        store = SpotifyTokenStore()
        client = SpotifyClient(token_store=store)
        # If the user is not authenticated, fail fast with a clear error.
        _ = store.load()
        if _ is None:
            raise SpotifyError("Not authenticated.")
        return import_liked_tracks(job_id=job_id, jobs=_jobs, client=client)

    _jobs.start_background(job_id, _run)
    return {"job_id": job_id}


@router.post("/playlists")
def import_playlists_job() -> dict:
    job_id = _jobs.create("spotify_import_playlists")

    def _run() -> dict:
        store = SpotifyTokenStore()
        client = SpotifyClient(token_store=store)
        tok = store.load()
        if tok is None:
            raise SpotifyError("Not authenticated.")
        return import_playlists(job_id=job_id, jobs=_jobs, client=client)

    _jobs.start_background(job_id, _run)
    return {"job_id": job_id}

