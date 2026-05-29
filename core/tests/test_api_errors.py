
from fastapi.testclient import TestClient

from app.database.engine import reset_engine
from app.database.init_db import init_db
from app.main import create_app


def test_api_error_envelope(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "errors.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    client = TestClient(create_app())
    resp = client.get("/api/v1/jobs/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["retryable"] is False
