from __future__ import annotations

import time

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.features.enrichment import ReccoBeatsEnrichmentService
from app.main import create_app
from tests.fixtures.library_seed import seed_library
from tests.fixtures.reccobeats_responses import batch_response_for_spotify_ids


def _slow_batch_handler(request: httpx.Request) -> httpx.Response:
    import json

    if request.url.path == "/v1/audio-features":
        ids = [p.strip() for p in request.url.params.get("ids", "").split(",") if p.strip()]
        payload = batch_response_for_spotify_ids(ids)
        return httpx.Response(
            200,
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
    return httpx.Response(404, content=b"{}")


def test_cancel_running_enrichment_job(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "cancel.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)

    transport = httpx.MockTransport(_slow_batch_handler)
    from app.reccobeats.client import ReccoBeatsClient

    client = ReccoBeatsClient(transport=transport, sleeper=lambda s: time.sleep(min(s, 0.05)))
    original_batch = client.get_audio_features_batch

    def slow_batch(ids: list[str]):
        time.sleep(0.4)
        return original_batch(ids)

    client.get_audio_features_batch = slow_batch  # type: ignore[method-assign]
    svc = ReccoBeatsEnrichmentService(client=client, sleeper=lambda _: None)

    job_id = svc.start_enrichment_job(only_missing=True, limit=5)
    time.sleep(0.1)

    api = TestClient(create_app())
    res = api.post(f"/api/v1/jobs/{job_id}/cancel")
    assert res.status_code == 200

    for _ in range(80):
        job = svc._jobs.get(job_id)
        assert job is not None
        if job.status == "cancelled":
            break
        time.sleep(0.05)
    assert job is not None
    assert job.status == "cancelled"
