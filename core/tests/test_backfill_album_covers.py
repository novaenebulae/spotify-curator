import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.database.models_library import Album
from scripts.backfill_album_covers import run


def test_backfill_updates_cover_from_raw_json(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "backfill.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()
    now = datetime(2026, 1, 1, 12, 0, 0)
    album_json = {
        "id": "sp_al_1",
        "name": "Test Album",
        "images": [{"url": "https://i.scdn.co/image/x", "width": 64, "height": 64}],
    }
    engine = get_engine()
    with Session(engine) as session:
        session.add(
            Album(
                name="Test Album",
                normalized_name="test album",
                raw_json=json.dumps(album_json),
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    stats = run(dry_run=False)
    assert stats["updated"] == 1

    with Session(engine) as session:
        album = session.execute(select(Album)).scalar_one()
        assert album.cover_image_url == "https://i.scdn.co/image/x"
        assert album.cover_image_width == 64
