from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models_library import LikedTrack, SpotifyTrack
from app.database.models_playlists import Playlist, PlaylistTrack
from app.playlists.rule_schemas import PlaylistRule, ValidationIssue


def select_candidate_track_ids(
    session: Session,
    rule: PlaylistRule,
) -> tuple[list[int], list[ValidationIssue]]:
    warnings: list[ValidationIssue] = []
    src = rule.source

    if src.clusters_include or src.clusters_exclude:
        warnings.append(
            ValidationIssue(
                code="CLUSTER_SOURCE_NOT_AVAILABLE_YET",
                message="Cluster filters ignored in phase 5",
                path="source",
            )
        )
    if src.seed_tracks:
        warnings.append(
            ValidationIssue(
                code="SEED_TRACKS_NOT_AVAILABLE_IN_PHASE_5",
                message="Seed tracks ignored in phase 5",
                path="source.seed_tracks",
            )
        )

    ids: set[int] = set()

    if src.liked_tracks:
        rows = session.execute(
            select(SpotifyTrack.track_id)
            .join(LikedTrack, LikedTrack.spotify_track_id == SpotifyTrack.spotify_track_id)
            .where(LikedTrack.is_current.is_(True))
        ).scalars()
        ids.update(rows)

    if src.playlists_include:
        sp_ids = session.execute(
            select(Playlist.spotify_playlist_id).where(Playlist.id.in_(src.playlists_include))
        ).scalars()
        sp_list = list(sp_ids)
        if sp_list:
            rows = session.execute(
                select(SpotifyTrack.track_id)
                .join(
                    PlaylistTrack,
                    PlaylistTrack.spotify_track_id == SpotifyTrack.spotify_track_id,
                )
                .where(
                    PlaylistTrack.spotify_playlist_id.in_(sp_list),
                    PlaylistTrack.is_current.is_(True),
                )
            ).scalars()
            ids.update(rows)

    if src.track_ids_include:
        ids.update(src.track_ids_include)

    if src.playlists_exclude:
        sp_ids = session.execute(
            select(Playlist.spotify_playlist_id).where(Playlist.id.in_(src.playlists_exclude))
        ).scalars()
        sp_list = list(sp_ids)
        if sp_list:
            excluded = set(
                session.execute(
                    select(SpotifyTrack.track_id)
                    .join(
                        PlaylistTrack,
                        PlaylistTrack.spotify_track_id == SpotifyTrack.spotify_track_id,
                    )
                    .where(
                        PlaylistTrack.spotify_playlist_id.in_(sp_list),
                        PlaylistTrack.is_current.is_(True),
                    )
                ).scalars()
            )
            ids -= excluded

    if src.track_ids_exclude:
        ids -= set(src.track_ids_exclude)

    return sorted(ids), warnings
