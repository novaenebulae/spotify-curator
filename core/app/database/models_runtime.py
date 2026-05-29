from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class DockerRuntimeCheck(Base):
    __tablename__ = "docker_runtime_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    check_name: Mapped[str] = mapped_column(String(128), nullable=False)
    service_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    image_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    image_tag: Mapped[str | None] = mapped_column(String(128), nullable=True)
    command: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
