
from fastapi.testclient import TestClient

from app.database.engine import reset_engine
from app.database.init_db import init_db
from app.main import create_app


def test_runtime_config(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "runtime.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test-client")
    from app.settings.config import settings

    monkeypatch.setattr(settings, "spotify_client_id", "test-client")
    reset_engine()
    init_db()

    client = TestClient(create_app())
    resp = client.get("/api/v1/runtime/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database_configured"] is True
    assert body["spotify_client_id_configured"] is True
    assert "access_token" not in str(body).lower()
    assert "refresh_token" not in str(body).lower()
