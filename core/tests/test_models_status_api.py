from __future__ import annotations

from fastapi.testclient import TestClient

from app.database.engine import reset_engine
from app.database.init_db import init_db
from app.main import create_app
from app.settings.config import settings


def test_models_status_endpoint(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "models_api.sqlite"
    models_dir = tmp_path / "essentia_models"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setattr(settings, "essentia_models_dir", str(models_dir))
    reset_engine()
    init_db()

    client = TestClient(create_app())
    res = client.get("/api/v1/models/status")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "summary" in data
    assert "profiles" in data
    assert len(data["models"]) > 0
    assert data["summary"]["missing"] > 0
    assert data["summary"]["real_inference_ready"] is False
    assert data["summary"]["total"] == len(data["models"])
