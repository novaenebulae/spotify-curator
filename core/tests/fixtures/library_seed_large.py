from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

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
from app.database.models_playlists import Playlist, PlaylistTrack


def seed_large_library(session: Session, *, track_count: int = 5000) -> None:
    """Seed many tracks for performance regression tests."""
    now = datetime(2026, 1, 15, 12, 0, 0)
    album = Album(
        name="Perf Album",
        normalized_name="perf album",
        release_date="2020-01-01",
        raw_json="{}",
        created_at=now,
        updated_at=now,
    )
    artist = Artist(
        name="Perf Artist",
        normalized_name="perf artist",
        raw_json="{}",
        created_at=now,
        updated_at=now,
    )
    session.add_all([album, artist])
    session.flush()

    sp_album = SpotifyAlbum(
        spotify_album_id="sp_album_perf",
        album_id=album.id,
        raw_json="{}",
    )
    sp_artist = SpotifyArtist(
        spotify_artist_id="sp_artist_perf",
        artist_id=artist.id,
        raw_json="{}",
    )
    playlist = Playlist(
        spotify_playlist_id="sp_pl_perf",
        spotify_uri="spotify:playlist:perf",
        name="Perf Playlist",
        raw_json="{}",
    )
    session.add_all([sp_album, sp_artist, playlist])
    session.flush()

    tracks: list[Track] = []
    for i in range(track_count):
        tracks.append(
            Track(
                name=f"Perf Track {i:05d}",
                normalized_title=f"perf track {i:05d}",
                duration_ms=180000 + (i % 120000),
                explicit=False,
                popularity=i % 100,
                preview_url=None,
                external_url=f"https://open.spotify.com/track/{i}",
                raw_json="{}",
                created_at=now,
                updated_at=now,
            )
        )
    session.add_all(tracks)
    session.flush()

    spotify_rows: list[SpotifyTrack] = []
    liked_rows: list[LikedTrack] = []
    ext_rows: list[ExternalId] = []
    ta_rows: list[TrackArtist] = []
    pl_rows: list[PlaylistTrack] = []

    for idx, track in enumerate(tracks):
        sp_id = f"sp_track_{idx:06d}"
        spotify_rows.append(
            SpotifyTrack(
                spotify_track_id=sp_id,
                track_id=track.id,
                spotify_uri=f"spotify:track:{sp_id}",
                album_id=album.id,
                market_status="available",
                is_playable=True,
                last_seen_at=now,
                raw_json="{}",
            )
        )
        if idx % 2 == 0:
            liked_rows.append(
                LikedTrack(
                    spotify_track_id=sp_id,
                    added_at=now - timedelta(days=idx % 365),
                    is_current=True,
                    raw_json="{}",
                )
            )
        ext_rows.append(
            ExternalId(
                track_id=track.id,
                id_type="isrc",
                id_value=f"ISRC{idx:08d}",
                source="spotify",
                external_type="isrc",
            )
        )
        ta_rows.append(TrackArtist(track_id=track.id, artist_id=artist.id, position=0))
        if idx % 10 == 0:
            pl_rows.append(
                PlaylistTrack(
                    spotify_playlist_id=playlist.spotify_playlist_id,
                    spotify_track_id=sp_id,
                    position=idx // 10,
                    added_at=now,
                    is_current=True,
                    raw_json="{}",
                )
            )

    session.add_all(spotify_rows)
    session.add_all(liked_rows)
    session.add_all(ext_rows)
    session.add_all(ta_rows)
    session.add_all(pl_rows)
    session.commit()
