from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_library import Track
from app.database.repositories.track_advanced_features import (
    AdvancedFeatureUpsertRow,
    TrackAdvancedFeaturesRepository,
)


def _seed_track(session: Session, track_id: int = 1) -> None:
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    session.add(
        Track(
            id=track_id,
            name="t",
            normalized_title="t",
            duration_ms=60_000,
            created_at=now,
            updated_at=now,
        )
    )
    session.flush()


def test_upsert_many_idempotent(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "taf.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    repo = TrackAdvancedFeaturesRepository()
    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session)
        repo.upsert_many(
            session,
            [
                AdvancedFeatureUpsertRow(
                    track_id=1,
                    feature_name="mood_happy_score",
                    value_float=0.5,
                    confidence=0.8,
                    source="essentia_tensorflow",
                    model_name="mood_happy",
                    pipeline_version="essentia_tensorflow_v1",
                )
            ],
        )
        session.commit()
        rows = repo.list_for_tracks(session, [1])
        assert len(rows) == 1
        assert rows[0].value_float == 0.5

        repo.upsert_many(
            session,
            [
                AdvancedFeatureUpsertRow(
                    track_id=1,
                    feature_name="mood_happy_score",
                    value_float=0.9,
                    confidence=0.9,
                    source="essentia_tensorflow",
                    model_name="mood_happy",
                    pipeline_version="essentia_tensorflow_v1",
                )
            ],
        )
        session.commit()
        rows = repo.list_for_tracks(session, [1])
        assert len(rows) == 1
        assert rows[0].value_float == 0.9
