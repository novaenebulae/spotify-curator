from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database.engine import reset_engine
from app.database.init_db import init_db
from app.main import create_app
from app.observability.diagnostics import CheckResult


def test_docker_checks_persisted(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "docker_checks.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    fake_results = [
        CheckResult(
            check_name="docker_available",
            command="docker version",
            exit_code=0,
            stdout="ok",
            stderr=None,
            success=True,
        )
    ]

    with patch("app.api.v1.runtime.run_docker_checks", return_value=fake_results):
        items = [{"check_name": "docker_available"}]
        with patch("app.api.v1.runtime.persist_checks", return_value=items):
            client = TestClient(create_app())
            post = client.post("/api/v1/runtime/docker/checks/run")
            assert post.status_code == 200
            assert "job_id" in post.json()

    client = TestClient(create_app())
    items = [{"check_name": "docker_available"}]
    with patch("app.api.v1.runtime.list_recent_checks", return_value=items):
        resp = client.get("/api/v1/runtime/docker/checks")
        assert resp.status_code == 200
        assert resp.json()["items"]
