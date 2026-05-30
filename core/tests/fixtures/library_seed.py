from __future__ import annotations

from datetime import datetime

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


def seed_library(session: Session) -> dict[str, int | str]:
    """Seed a small library dataset for phase 2 tests."""
    now = datetime(2026, 1, 15, 12, 0, 0)

    album_a = Album(
        name="Alpha Album",
        normalized_name="alpha album",
        release_date="2020-01-01",
        raw_json="{}",
        created_at=now,
        updated_at=now,
    )
    album_b = Album(
        name="Beta Album",
        normalized_name="beta album",
        release_date="2021-06-01",
        raw_json="{}",
        created_at=now,
        updated_at=now,
    )
    session.add_all([album_a, album_b])
    session.flush()

    session.add_all(
        [
            SpotifyAlbum(
                spotify_album_id="sp_album_a",
                album_id=album_a.id,
                spotify_uri="spotify:album:a",
                raw_json="{}",
            ),
            SpotifyAlbum(
                spotify_album_id="sp_album_b",
                album_id=album_b.id,
                spotify_uri="spotify:album:b",
                raw_json="{}",
            ),
        ]
    )

    artist_x = Artist(
        name="Artist X",
        normalized_name="artist x",
        raw_json="{}",
        created_at=now,
        updated_at=now,
    )
    artist_y = Artist(
        name="Artist Y",
        normalized_name="artist y",
        raw_json="{}",
        created_at=now,
        updated_at=now,
    )
    session.add_all([artist_x, artist_y])
    session.flush()

    session.add_all(
        [
            SpotifyArtist(
                spotify_artist_id="sp_artist_x",
                artist_id=artist_x.id,
                spotify_uri="spotify:artist:x",
                raw_json="{}",
            ),
            SpotifyArtist(
                spotify_artist_id="sp_artist_y",
                artist_id=artist_y.id,
                spotify_uri="spotify:artist:y",
                raw_json="{}",
            ),
        ]
    )

    tracks_data = [
        ("Track One", "track one", 180000, "sp_t1", "ISRC111", album_a.id, True),
        ("Track Two", "track two", 200000, "sp_t2", "ISRC222", album_b.id, True),
        ("Track Three", "track three", 240000, "sp_t3", "ISRC111", album_a.id, False),
        ("Long Track", "long track", 360000, "sp_t4", "ISRC444", album_b.id, False),
    ]
    ids: dict[str, int | str] = {}
    for name, norm, dur, sp_id, isrc, album_id, liked in tracks_data:
        t = Track(
            name=name,
            normalized_title=norm,
            duration_ms=dur,
            explicit=False,
            popularity=50,
            raw_json="{}",
            created_at=now,
            updated_at=now,
        )
        session.add(t)
        session.flush()
        session.add(
            SpotifyTrack(
                spotify_track_id=sp_id,
                track_id=t.id,
                album_id=album_id,
                spotify_uri=f"spotify:track:{sp_id}",
                market_status="available",
                raw_json="{}",
                last_seen_at=now,
            )
        )
        session.add(
            TrackArtist(
                track_id=t.id,
                artist_id=artist_x.id if "One" in name or "Three" in name else artist_y.id,
                position=0,
            )
        )
        session.add(
            ExternalId(
                track_id=t.id,
                id_type="isrc",
                id_value=isrc,
                source="spotify",
                external_type="isrc",
                confidence=1.0,
            )
        )
        if liked:
            session.add(
                LikedTrack(
                    spotify_track_id=sp_id,
                    added_at=datetime(2026, 2, 1, 10, 0, 0),
                    is_current=True,
                    raw_json="{}",
                )
            )
        ids[sp_id] = t.id

    pl = Playlist(
        spotify_playlist_id="sp_pl_1",
        spotify_uri="spotify:playlist:1",
        name="My Playlist",
        raw_json="{}",
    )
    session.add(pl)
    session.flush()
    session.add(
        PlaylistTrack(
            spotify_playlist_id="sp_pl_1",
            position=0,
            spotify_track_id="sp_t1",
            is_current=True,
            raw_json="{}",
        )
    )
    session.commit()

    ids["playlist_id"] = pl.id
    ids["spotify_playlist_id"] = "sp_pl_1"
    return ids
