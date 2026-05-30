from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class LibraryAction(Base):
    __tablename__ = "library_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="previewed", index=True
    )
    filter_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")
    selected_track_ids_json: Mapped[str] = mapped_column(
        String(100000), nullable=False, default="[]"
    )
    affected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    spotify_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    result_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")
    warning_json: Mapped[str | None] = mapped_column(String(100000), nullable=True)
    created_by_context: Mapped[str] = mapped_column(String(32), nullable=False, default="api")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
