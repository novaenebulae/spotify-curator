from __future__ import annotations

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine, reset_engine
from app.database.init_db import init_db
from app.main import create_app
from app.previews.upsert import PreviewUpsertService
from app.previews.schemas import PreviewCandidate
from tests.fixtures.library_seed import seed_library


def test_preview_stream_proxies_mp3(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'stream.sqlite'}")
    reset_engine()
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
        PreviewUpsertService().upsert_candidate(
            session,
            track_id=1,
            candidate=PreviewCandidate(
                provider="deezer",
                provider_track_id="3135556",
                provider_url=None,
                preview_url="https://cdnt-preview.dzcdn.net/stream/expired.mp3",
                title="Test",
                artist="Artist",
                album=None,
                isrc=None,
                provider_duration_seconds=30.0,
                expected_duration_seconds=30.0,
                duration_delta_seconds=0.0,
                match_score=1.0,
                match_confidence=0.95,
                is_available=True,
            ),
        )
        session.commit()

    fake_mp3 = b"ID3fake-preview-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        if "dzcdn" in str(request.url):
            return httpx.Response(200, content=fake_mp3, headers={"content-type": "audio/mpeg"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "app.previews.deezer_preview_refresh.is_deezer_preview_url_expired",
        lambda url, **kw: False,
    )
    monkeypatch.setattr(
        "app.api.v1.previews.fetch_track_preview_audio",
        lambda session, track_id, **kw: (
            fake_mp3,
            "audio/mpeg",
        ),
    )

    client = TestClient(create_app())
    res = client.get("/api/v1/tracks/1/preview/stream")
    assert res.status_code == 200
    assert res.content == fake_mp3
    assert "audio" in res.headers.get("content-type", "")

    meta = client.get("/api/v1/tracks/1/preview")
    assert meta.status_code == 200
    assert meta.json()["playback_url"] == "/api/v1/tracks/1/preview/stream"
