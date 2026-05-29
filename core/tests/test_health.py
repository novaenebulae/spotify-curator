from fastapi.testclient import TestClient

from app.main import create_app


def test_health_ok() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "spotify-curator-core"
    assert body["version"] == "0.1.0"

