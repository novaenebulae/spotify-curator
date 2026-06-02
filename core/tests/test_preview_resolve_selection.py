from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.repositories.track_previews import TrackPreviewsRepository
from tests.fixtures.library_seed import seed_library


def test_list_track_ids_missing_no_limit(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "preview_sel.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()
    engine = get_engine()
    repo = TrackPreviewsRepository()

    with Session(engine) as session:
        seed = seed_library(session)
        track_with_preview = int(seed["sp_t1"])
        track_missing = int(seed["sp_t2"])
        repo.upsert(
            session,
            track_id=track_with_preview,
            provider="deezer",
            fields={
                "is_available": True,
                "preview_url": "https://example.com/preview.mp3",
            },
        )
        session.commit()

        limited = repo.list_track_ids_missing(session, provider="deezer", limit=1)
        assert len(limited) == 1

        all_missing = repo.list_track_ids_missing(session, provider="deezer", limit=None)
        assert track_with_preview not in all_missing
        assert track_missing in all_missing
