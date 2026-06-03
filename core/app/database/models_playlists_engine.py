from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class PlaylistRule(Base):
    __tablename__ = "playlist_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    rule_yaml: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class GeneratedPlaylist(Base):
    __tablename__ = "generated_playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playlist_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("playlist_rules.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="previewed", index=True)
    target_size: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    actual_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engine_version: Mapped[str] = mapped_column(String(64), nullable=False, default="playlist_engine_v1")
    score_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    warning_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class GeneratedPlaylistItem(Base):
    __tablename__ = "generated_playlist_items"
    __table_args__ = (Index("ix_generated_playlist_items_gp_track", "generated_playlist_id", "track_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generated_playlist_id: Mapped[int] = mapped_column(
        ForeignKey("generated_playlists.id"), nullable=False, index=True
    )
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    final_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    selected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    exclusion_details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True, index=True)
    generated_playlist_id: Mapped[int] = mapped_column(
        ForeignKey("generated_playlists.id"), nullable=False, index=True
    )
    target_spotify_playlist_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sync_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="replace")
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="previewed", index=True)
    diff_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sync_job_id: Mapped[int] = mapped_column(ForeignKey("sync_jobs.id"), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
