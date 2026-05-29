from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    normalized_title: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", index=True
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    explicit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preview_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    raw_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    normalized_name: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", index=True
    )
    raw_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    normalized_name: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", index=True
    )
    release_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class TrackArtist(Base):
    __tablename__ = "track_artists"

    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), primary_key=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SpotifyTrack(Base):
    __tablename__ = "spotify_tracks"

    spotify_track_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False, unique=True)
    spotify_uri: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    is_playable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    available_markets_json: Mapped[str] = mapped_column(
        String(100000), nullable=False, default="[]"
    )
    linked_from_spotify_track_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    restrictions_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")
    market_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="unknown", index=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    raw_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")


class SpotifyArtist(Base):
    __tablename__ = "spotify_artists"

    spotify_artist_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"), nullable=False, unique=True)
    spotify_uri: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    raw_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")


class SpotifyAlbum(Base):
    __tablename__ = "spotify_albums"

    spotify_album_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id"), nullable=False, unique=True)
    spotify_uri: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    raw_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")


class ExternalId(Base):
    __tablename__ = "external_ids"
    __table_args__ = (UniqueConstraint("track_id", "id_type", name="uq_external_ids_track_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    id_type: Mapped[str] = mapped_column(String(64), nullable=False)
    id_value: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="spotify")
    external_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class LikedTrack(Base):
    __tablename__ = "liked_tracks"

    spotify_track_id: Mapped[str] = mapped_column(
        ForeignKey("spotify_tracks.spotify_track_id"),
        primary_key=True,
    )
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    raw_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")
