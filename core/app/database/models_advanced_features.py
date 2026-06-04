from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class TrackAdvancedFeature(Base):
    __tablename__ = "track_advanced_features"
    __table_args__ = (
        UniqueConstraint(
            "track_id",
            "feature_name",
            "source",
            "model_name",
            "pipeline_version",
            name="uq_track_advanced_features_track_feature_source",
        ),
        Index("ix_track_advanced_features_track_id", "track_id"),
        Index("ix_track_advanced_features_feature_name", "feature_name"),
        Index("ix_track_advanced_features_source", "source"),
        Index("ix_track_advanced_features_status", "status"),
        Index(
            "ix_track_advanced_features_track_feature",
            "track_id",
            "feature_name",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    feature_name: Mapped[str] = mapped_column(String(64), nullable=False)
    value_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    value_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pipeline_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aggregation_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
