from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.main import create_app
from tests.fixtures.library_seed import seed_library


def test_library_summary(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "summary.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
    client = TestClient(create_app())
    res = client.get("/api/v1/library/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["tracks_total"] == 4
    assert data["playlists_total"] == 1
    assert "spotify_connected" in data
