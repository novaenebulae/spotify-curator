from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class FeatureSource(Base):
    __tablename__ = "feature_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="api")
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_audio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_api_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class AudioFeature(Base):
    __tablename__ = "audio_features"
    __table_args__ = (
        Index(
            "uq_audio_features_active_track_source",
            "track_id",
            "feature_source_id",
            unique=True,
            sqlite_where="is_active = 1",
        ),
        Index("ix_audio_features_track_id", "track_id"),
        Index("ix_audio_features_feature_source_id", "feature_source_id"),
        Index("ix_audio_features_track_source", "track_id", "feature_source_id"),
        Index(
            "ix_audio_features_track_source_active",
            "track_id",
            "feature_source_id",
            "is_active",
        ),
        Index("ix_audio_features_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    feature_source_id: Mapped[int] = mapped_column(ForeignKey("feature_sources.id"), nullable=False)
    external_track_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    bpm_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    danceability: Mapped[float | None] = mapped_column(Float, nullable=True)
    danceability_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    valence: Mapped[float | None] = mapped_column(Float, nullable=True)
    valence_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    acousticness: Mapped[float | None] = mapped_column(Float, nullable=True)
    acousticness_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    instrumentalness: Mapped[float | None] = mapped_column(Float, nullable=True)
    instrumentalness_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    speechiness: Mapped[float | None] = mapped_column(Float, nullable=True)
    speechiness_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    liveness: Mapped[float | None] = mapped_column(Float, nullable=True)
    liveness_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    loudness: Mapped[float | None] = mapped_column(Float, nullable=True)
    loudness_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    key: Mapped[int | None] = mapped_column(Integer, nullable=True)
    key_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    mode: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mode_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_signature: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feature_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class AudioFeatureRawPayload(Base):
    __tablename__ = "audio_feature_raw_payloads"
    __table_args__ = (
        Index("ix_audio_feature_raw_payloads_track_source", "track_id", "feature_source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    feature_source_id: Mapped[int] = mapped_column(ForeignKey("feature_sources.id"), nullable=False)
    request_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
