from __future__ import annotations

import json
import time
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_features import AudioFeature
from app.features.enrichment import ReccoBeatsEnrichmentService
from app.features.upsert import FeatureUpsertService
from app.jobs.service import JobService
from app.main import create_app
from app.reccobeats.client import ReccoBeatsClient
from tests.fixtures.library_seed import seed_library
from tests.fixtures.reccobeats_responses import (
    SAMPLE_FEATURES,
    SAMPLE_TRACK,
    batch_response_for_spotify_ids,
)


def _json_response(status: int, payload: dict | list | None) -> httpx.Response:
    content = json.dumps(payload).encode() if payload is not None else b""
    return httpx.Response(status, content=content, headers={"Content-Type": "application/json"})


def _mock_handler(spotify_to_track: dict[str, dict] | None = None) -> httpx.MockTransport:
    batch_calls: list[str] = []
    per_track_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/audio-features" and request.method == "GET":
            ids_param = request.url.params.get("ids", "")
            ids = [part.strip() for part in ids_param.split(",") if part.strip()]
            batch_calls.append(ids_param)
            return _json_response(200, batch_response_for_spotify_ids(ids))
        if request.url.path == "/v1/track" or request.url.path.endswith("/audio-features"):
            per_track_calls.append(str(request.url))
            return _json_response(404, {"error": "deprecated per-track path"})
        return _json_response(404, {"error": "not found"})

    transport = httpx.MockTransport(handler)
    transport.batch_calls = batch_calls  # type: ignore[attr-defined]
    transport.per_track_calls = per_track_calls  # type: ignore[attr-defined]
    return transport


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "enrich.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
    return TestClient(create_app())


def _enrichment_service(
    transport: httpx.BaseTransport,
) -> ReccoBeatsEnrichmentService:
    client = ReccoBeatsClient(transport=transport, sleeper=lambda _: None)
    return ReccoBeatsEnrichmentService(client=client, sleeper=lambda _: None)


def test_enrich_only_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'enrich.sqlite'}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)

    transport = _mock_handler()
    svc = _enrichment_service(transport)
    job_id = svc.start_enrichment_job(only_missing=True, limit=1)

    for _ in range(100):
        job = svc._jobs.get(job_id)
        assert job is not None
        if job.status in ("succeeded", "failed"):
            break
        time.sleep(0.05)

    job = svc._jobs.get(job_id)
    assert job is not None
    assert job.status == "succeeded"
    assert job.result_json["succeeded"] == 1
    assert job.result_json.get("http_batches", 0) >= 1
    assert len(transport.batch_calls) == 1  # type: ignore[attr-defined]
    assert len(transport.per_track_calls) == 0  # type: ignore[attr-defined]

    with Session(engine) as session:
        active = session.query(AudioFeature).filter(AudioFeature.is_active.is_(True)).all()
    assert len(active) == 1
    assert active[0].status == "success"


def test_enrich_idempotent_only_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'enrich2.sqlite'}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)

    transport = _mock_handler()
    svc = _enrichment_service(transport)
    job_id1 = svc._jobs.create("reccobeats_enrichment")
    stats1 = svc.run_enrichment(job_id1, track_ids=[1], only_missing=True)
    job_id2 = svc._jobs.create("reccobeats_enrichment")
    stats2 = svc.run_enrichment(job_id2, track_ids=[1], only_missing=True)

    assert stats1["succeeded"] == 1
    assert stats2["succeeded"] == 0

    with Session(engine) as session:
        count = (
            session.query(AudioFeature)
            .filter(AudioFeature.track_id == 1, AudioFeature.is_active.is_(True))
            .count()
        )
    assert count == 1


def test_enrich_force_refresh(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'refresh.sqlite'}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)

    transport = _mock_handler()
    svc = _enrichment_service(transport)
    job_id = svc._jobs.create("reccobeats_enrichment")
    svc.run_enrichment(job_id, only_missing=True, limit=1, force_refresh=False)

    job_id2 = svc._jobs.create("reccobeats_enrichment")
    svc.run_enrichment(job_id2, track_ids=[1], force_refresh=True)

    with Session(engine) as session:
        rows = session.query(AudioFeature).filter(AudioFeature.track_id == 1).all()
    assert len(rows) == 2
    active = [r for r in rows if r.is_active]
    assert len(active) == 1


def test_enrich_retry_failed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'retry.sqlite'}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed = seed_library(session)
        track_id = int(seed["sp_t1"])
        from app.features.reccobeats_mapper import NormalizedFeatureRow
        from app.reccobeats.schemas import ReccoBeatsFetchResult

        upsert = FeatureUpsertService()
        upsert.upsert_reccobeats(
            session,
            track_id=track_id,
            fetch_result=ReccoBeatsFetchResult(track=None, features=None),
            normalized=NormalizedFeatureRow(
                status="failed",
                error_code="TEST",
                error_message="fail",
            ),
            replace_failed=True,
        )
        session.commit()

    transport = _mock_handler()
    svc = _enrichment_service(transport)
    job_id = svc._jobs.create("reccobeats_enrichment")
    stats = svc.run_enrichment(job_id, retry_failed=True, only_missing=False)

    assert stats["succeeded"] >= 1


def test_enrich_api_endpoint(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    transport = _mock_handler()

    with patch("app.api.v1.features._enrichment") as mock_svc:
        mock_inner = _enrichment_service(transport)
        mock_svc.start_enrichment_job.side_effect = mock_inner.start_enrichment_job
        res = client.post(
            "/api/v1/features/reccobeats/enrich",
            json={"only_missing": True, "limit": 1},
        )
    assert res.status_code == 200
    body = res.json()
    assert "job_id" in body
    assert body["status"] == "pending"


def test_job_already_running_returns_409(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "running.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)

    from datetime import UTC, datetime

    from app.database.models_jobs import Job

    with Session(engine) as session:
        session.add(
            Job(
                id="running123",
                job_type="reccobeats_enrichment",
                status="running",
                progress_current=0,
                progress_total=10,
                current_step="enriching_tracks",
                attempt_count=1,
                max_attempts=3,
                result_json="{}",
                last_error="",
                created_at=datetime.now(tz=UTC).replace(tzinfo=None),
            )
        )
        session.commit()

    with JobService._active_lock:
        JobService._active_ids.add("running123")
    try:
        client = TestClient(create_app())
        res = client.post("/api/v1/features/reccobeats/enrich", json={"only_missing": True, "limit": 1})
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "JOB_ALREADY_RUNNING"
    finally:
        with JobService._active_lock:
            JobService._active_ids.discard("running123")
