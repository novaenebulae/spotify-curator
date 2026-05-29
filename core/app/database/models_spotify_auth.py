from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class SpotifyAuthToken(Base):
    __tablename__ = "spotify_auth_tokens"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    access_token: Mapped[str] = mapped_column(String(2048), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    token_type: Mapped[str] = mapped_column(String(32), nullable=False, default="Bearer")
    scope: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    raw_json: Mapped[str] = mapped_column(String(100000), nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

