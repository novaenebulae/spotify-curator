from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.database.engine import reset_engine
from app.database.init_db import init_db
from app.main import create_app
from app.settings.config import settings


def _fake_download(url: str, dest: Path, timeout: int) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"fake-bytes")
    return len(b"fake-bytes")


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "models_api.sqlite"
    models_dir = tmp_path / "essentia_models"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setattr(settings, "essentia_models_dir", str(models_dir))
    monkeypatch.setattr(settings, "essentia_models_accept_license", False)
    monkeypatch.setattr("app.models_registry.manager._http_download", _fake_download)
    reset_engine()
    init_db()
    return TestClient(create_app())


def test_models_status_shape(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/models/status")
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data and "profiles" in data and "models" in data
    assert data["summary"]["missing"] > 0
    assert data["summary"]["real_inference_ready"] is False
    assert data["summary"]["default_profile"] == "phase6-recommended"
    assert len(data["models"]) == 17
    names = {p["name"] for p in data["profiles"]}
    assert {"phase6-minimal", "phase6-recommended", "phase6-full"}.issubset(names)


def test_download_profile_then_verify(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.post(
        "/api/v1/models/download-profile",
        json={"profile": "phase6-minimal", "accept_license": True},
    )
    assert res.status_code == 200
    body = res.json()
    keys = {row["model_key"] for row in body["models"]}
    assert "discogs_effnet_bs64" in keys
    assert "discogs_maest_30s_pw_519l" not in keys

    verify = client.post("/api/v1/models/verify", json={"model_key": "discogs_effnet_bs64"})
    assert verify.status_code == 200
    vdata = verify.json()
    assert vdata["status"] == "available"
    assert vdata["weights_exists"] is True
    assert vdata["metadata_exists"] is True


def test_download_single_model(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.post(
        "/api/v1/models/download",
        json={"model_key": "mood_happy_discogs_effnet", "accept_license": True},
    )
    assert res.status_code == 200
    keys = {row["model_key"] for row in res.json()["downloaded"]}
    # head + its extractor dependency
    assert "mood_happy_discogs_effnet" in keys
    assert "discogs_effnet_bs64" in keys
