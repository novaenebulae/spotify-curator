from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_library import Track
from app.database.repositories.track_embeddings import (
    TrackEmbeddingUpsertRow,
    TrackEmbeddingsRepository,
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


def test_upsert_and_parse_vector(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "emb_repo.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    repo = TrackEmbeddingsRepository()
    vec = [0.1, 0.2, 0.3]
    engine = get_engine()
    with Session(engine) as session:
        _seed_track(session)
        row = repo.upsert(
            session,
            TrackEmbeddingUpsertRow(
                track_id=1,
                source="essentia_tensorflow",
                model_name="discogs-effnet-bs64-1.pb",
                dimension=3,
                vector_json=json.dumps(vec),
                pipeline_version="tf_v1",
                segments_used=2,
                confidence=0.9,
            ),
        )
        session.commit()
        assert row.dimension == 3
        parsed = repo.parse_vector(row)
        assert parsed == vec

        row2 = repo.upsert(
            session,
            TrackEmbeddingUpsertRow(
                track_id=1,
                source="essentia_tensorflow",
                model_name="discogs-effnet-bs64-1.pb",
                dimension=3,
                vector_json=json.dumps([1.0, 1.0, 1.0]),
                pipeline_version="tf_v1",
            ),
        )
        session.commit()
        rows = repo.list_for_tracks(session, [1])
        assert len(rows) == 1
        assert rows[0].id == row2.id
