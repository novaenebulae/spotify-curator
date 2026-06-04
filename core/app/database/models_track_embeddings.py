from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class TrackEmbedding(Base):
    __tablename__ = "track_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "track_id",
            "source",
            "model_name",
            "pipeline_version",
            name="uq_track_embeddings_track_source_model",
        ),
        Index("ix_track_embeddings_track_id", "track_id"),
        Index("ix_track_embeddings_source", "source"),
        Index("ix_track_embeddings_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    aggregation_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    segments_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pipeline_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
