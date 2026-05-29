from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class OAuthPkceState(Base):
    __tablename__ = "oauth_pkce_states"

    state: Mapped[str] = mapped_column(String(128), primary_key=True)
    code_verifier: Mapped[str] = mapped_column(String(256), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
