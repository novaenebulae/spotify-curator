from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_type: Mapped[str] = mapped_column(String(32), nullable=False)  # full|liked|playlists
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # completed|failed

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    track_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    playlist_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    metadata_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")


class LikedTrackSnapshot(Base):
    __tablename__ = "liked_track_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "spotify_track_id", name="uq_liked_track_snapshots"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"), nullable=False)
    spotify_track_id: Mapped[str] = mapped_column(
        ForeignKey("spotify_tracks.spotify_track_id"), nullable=False
    )
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class PlaylistSnapshot(Base):
    __tablename__ = "playlist_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "spotify_playlist_id", name="uq_playlist_snapshots"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"), nullable=False)
    spotify_playlist_id: Mapped[str] = mapped_column(
        ForeignKey("playlists.spotify_playlist_id"), nullable=False
    )
    spotify_snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PlaylistTrackSnapshot(Base):
    __tablename__ = "playlist_track_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "spotify_playlist_id",
            "position",
            name="uq_playlist_track_snapshots_position",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"), nullable=False)
    spotify_playlist_id: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    spotify_track_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

