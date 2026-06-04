from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class JobItem(Base):
    __tablename__ = "job_items"
    __table_args__ = (
        Index("ix_job_items_job_status", "job_id", "status"),
        Index("ix_job_items_available", "status", "next_retry_at", "priority"),
        Index("ix_job_items_job_stage_status", "job_id", "stage_name", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    track_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tracks.id"), nullable=True, index=True)
    segment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    stage_name: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    depends_on_item_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("job_items.id"), nullable=True
    )
    consumer_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pipeline_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    input_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    worker_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    worker_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="starting")
    current_job_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("jobs.id"), nullable=True
    )
    current_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(256), nullable=True)
    process_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class JobEvent(Base):
    __tablename__ = "job_events"
    __table_args__ = (Index("ix_job_events_job_created", "job_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), nullable=False, index=True)
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    context_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
