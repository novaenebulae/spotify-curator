from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spotify_playlist_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    spotify_uri: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    owner_spotify_user_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    is_public: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    collaborative: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    spotify_snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    raw_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"
    __table_args__ = (
        UniqueConstraint(
            "spotify_playlist_id",
            "position",
            name="uq_playlist_tracks_playlist_position",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spotify_playlist_id: Mapped[str] = mapped_column(
        ForeignKey("playlists.spotify_playlist_id"), nullable=False
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # May be null when Spotify returns `track: null` for unavailable items.
    spotify_track_id: Mapped[str | None] = mapped_column(
        ForeignKey("spotify_tracks.spotify_track_id"), nullable=True
    )

    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    added_by_spotify_user_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    raw_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")

