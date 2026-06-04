from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.database.engine import reset_engine
from app.database.init_db import init_db
from app.main import create_app
from app.settings.config import settings


def test_download_without_license_is_refused(tmp_path, monkeypatch) -> None:
    calls: list[str] = []

    def _spy(url: str, dest: Path, timeout: int) -> int:
        calls.append(url)
        return 0

    db_path = tmp_path / "license.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setattr(settings, "essentia_models_dir", str(tmp_path / "models"))
    monkeypatch.setattr(settings, "essentia_models_accept_license", False)
    monkeypatch.setattr("app.models_registry.manager._http_download", _spy)
    reset_engine()
    init_db()

    client = TestClient(create_app())
    res = client.post(
        "/api/v1/models/download",
        json={"model_key": "discogs_effnet_bs64", "accept_license": False},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "MODEL_LICENSE_NOT_ACCEPTED"
    assert calls == []


def test_download_profile_without_license_is_refused(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "license2.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setattr(settings, "essentia_models_dir", str(tmp_path / "models"))
    monkeypatch.setattr(settings, "essentia_models_accept_license", False)
    reset_engine()
    init_db()

    client = TestClient(create_app())
    res = client.post(
        "/api/v1/models/download-profile",
        json={"profile": "phase6-minimal", "accept_license": False},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "MODEL_LICENSE_NOT_ACCEPTED"
