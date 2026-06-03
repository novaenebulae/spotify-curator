from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_library import SpotifyTrack
from app.database.repositories.generated_playlists import GeneratedPlaylistsRepository
from app.database.repositories.sync_jobs import SyncJobsRepository
from app.spotify.client import SpotifyClient
from app.spotify.token_store import SpotifyTokenStore


class SyncDryRunService:
    """Compare generated playlist with Spotify target — never writes."""

    def __init__(self) -> None:
        self._generated = GeneratedPlaylistsRepository()
        self._sync = SyncJobsRepository()

    def run(
        self,
        session: Session,
        *,
        generated_playlist_id: int,
        target_spotify_playlist_id: str | None,
        sync_mode: str,
    ) -> dict[str, Any]:
        gp = self._generated.get(session, generated_playlist_id)
        if gp is None:
            raise ValueError("GENERATED_PLAYLIST_NOT_FOUND")

        items = self._generated.list_items(session, generated_playlist_id)
        local_track_ids = [it.track_id for it in items]
        local_spotify_ids = self._spotify_ids_for_tracks(session, local_track_ids)

        warnings: list[str] = []
        target_items: list[str] = []
        target_name = ""

        if target_spotify_playlist_id:
            try:
                store = SpotifyTokenStore()
                stored = store.load()
                if stored is None:
                    warnings.append("SPOTIFY_NOT_AUTHENTICATED")
                else:
                    client = SpotifyClient(token_store=store)
                    target_items = self._read_playlist_track_ids(client, target_spotify_playlist_id)
                    warnings.extend(self._check_write_scope(stored.scope))
            except Exception as exc:
                warnings.append(f"SPOTIFY_READ_FAILED: {exc}")
        else:
            warnings.append("NO_TARGET_PLAYLIST_ID")

        local_set = set(local_spotify_ids)
        target_set = set(target_items)
        to_add = sorted(local_set - target_set)
        to_remove = sorted(target_set - local_set)
        unchanged = sorted(local_set & target_set)

        diff = {
            "to_add": to_add,
            "to_remove": to_remove,
            "unchanged": unchanged,
        }
        diff_json = json.dumps(diff)

        sync_job = self._sync.create(
            session,
            generated_playlist_id=generated_playlist_id,
            sync_mode=sync_mode,
            target_spotify_playlist_id=target_spotify_playlist_id,
            diff_json=diff_json,
            dry_run=True,
            status="previewed",
        )
        if warnings:
            self._sync.add_log(
                session,
                sync_job_id=sync_job.id,
                level="warning",
                message="; ".join(warnings),
            )
        session.commit()

        return {
            "sync_job_id": sync_job.id,
            "dry_run": True,
            "mode": sync_mode,
            "target_playlist": {
                "spotify_playlist_id": target_spotify_playlist_id,
                "name": target_name,
            },
            "diff": diff,
            "warnings": warnings,
        }

    def get_job(self, session: Session, sync_job_id: int) -> dict[str, Any] | None:
        row = self._sync.get(session, sync_job_id)
        if row is None:
            return None
        diff = json.loads(row.diff_json) if row.diff_json else {}
        return {
            "sync_job_id": row.id,
            "dry_run": row.dry_run,
            "mode": row.sync_mode,
            "status": row.status,
            "target_spotify_playlist_id": row.target_spotify_playlist_id,
            "diff": diff,
        }

    def _spotify_ids_for_tracks(self, session: Session, track_ids: list[int]) -> list[str]:
        if not track_ids:
            return []
        rows = session.execute(
            select(SpotifyTrack.spotify_track_id).where(SpotifyTrack.track_id.in_(track_ids))
        ).all()
        return [r[0] for r in rows if r[0]]

    def _read_playlist_track_ids(self, client: SpotifyClient, playlist_id: str) -> list[str]:
        ids: list[str] = []
        for item in client.iter_playlist_items(playlist_id=playlist_id):
            track = item.get("track") if isinstance(item, dict) else None
            if not track or not isinstance(track, dict):
                continue
            tid = track.get("id")
            if tid:
                ids.append(tid)
        return ids

    def _check_write_scope(self, scope: str) -> list[str]:
        warnings: list[str] = []
        if "playlist-modify-public" not in scope and "playlist-modify-private" not in scope:
            warnings.append("WRITE_SCOPE_NOT_AVAILABLE")
        return warnings
