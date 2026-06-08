from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.audio.hybrid_availability import HybridAvailabilityService
from app.database.engine import reset_engine
from app.database.init_db import init_db
from app.database.models_library import Track
from app.database.models_previews import TrackPreview


def _seed_track(session: Session, track_id: int = 1) -> None:
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    session.add(
        Track(
            id=track_id,
            name="t",
            normalized_title="t",
            duration_ms=180_000,
            created_at=now,
            updated_at=now,
        )
    )
    session.flush()


def _seed_deezer_preview(
    session: Session,
    *,
    track_id: int,
    confidence: float,
    is_available: bool,
) -> None:
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    session.add(
        TrackPreview(
            track_id=track_id,
            provider="deezer",
            preview_url="https://cdn.example/preview.mp3",
            match_confidence=confidence,
            is_available=is_available,
            created_at=now,
        )
    )


def test_deezer_for_analysis_trusts_resolver_is_available(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "hybrid.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setattr("app.audio.hybrid_availability.settings.deezer_preview_analysis_min_confidence", 0.70)
    reset_engine()
    init_db()

    svc = HybridAvailabilityService()
    from app.database.engine import get_engine

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session)
        _seed_deezer_preview(session, track_id=1, confidence=0.62, is_available=True)
        session.commit()
        ok, conf = svc.deezer_for_analysis(session, 1)
        assert ok is True
        assert conf == 0.62


def test_deezer_for_analysis_rejects_unavailable_preview(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "hybrid2.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    svc = HybridAvailabilityService()
    from app.database.engine import get_engine

    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session)
        _seed_deezer_preview(session, track_id=1, confidence=0.80, is_available=False)
        session.commit()
        ok, conf = svc.deezer_for_analysis(session, 1)
        assert ok is False
        assert conf == 0.0
