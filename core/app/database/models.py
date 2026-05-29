from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    value_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
