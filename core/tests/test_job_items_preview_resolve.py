from sqlalchemy.orm import Session

from app.database.models_jobs import Job
from app.jobs.items.constants import ITEM_TYPE_PREVIEW_RESOLVE_TRACK, WORKER_TYPE_PREVIEW_RESOLVER
from app.jobs.items.service import JobItemService
from app.jobs.service import JobService
from app.previews.deezer_client import DeezerClient
from app.previews.deezer_provider import DeezerPreviewProvider
from app.workers.preview_resolver_worker import PreviewResolverWorker
import json
from pathlib import Path

import httpx


def test_preview_resolve_item_success(audio_db, monkeypatch) -> None:
    db_url = str(audio_db.url)
    monkeypatch.setenv("DATABASE_URL", db_url)
    from app.database.engine import get_engine, reset_engine
    from app.settings.config import settings

    monkeypatch.setattr(settings, "deezer_preview_ui_min_confidence", 0.1)
    reset_engine()
    engine = get_engine()
    fixture = Path(__file__).parent / "fixtures" / "deezer_search_response.json"
    body = json.loads(fixture.read_text(encoding="utf-8"))
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=body))
    client = DeezerClient(transport=transport)
    provider = DeezerPreviewProvider(client=client)
    worker = PreviewResolverWorker(provider=provider)

    jobs = JobService()
    items = JobItemService()
    job_id = jobs.create("preview_resolve")
    with Session(engine) as session:
        from sqlalchemy import text

        session.execute(
            text(
                "UPDATE tracks SET name = 'Harder Better Faster Stronger', duration_ms = 224000 WHERE id = 1"
            )
        )
        session.execute(
            text(
                """
                INSERT INTO artists (id, name, normalized_name, raw_json, created_at, updated_at)
                VALUES (1, 'Daft Punk', 'daft punk', '{}', datetime('now'), datetime('now'))
                """
            )
        )
        session.execute(text("INSERT INTO track_artists (track_id, artist_id, position) VALUES (1, 1, 0)"))
        session.commit()
        job = session.get(Job, job_id)
        if job:
            job.progress_total = 1
        items.create_items_for_job(
            session,
            job_id=job_id,
            item_type=ITEM_TYPE_PREVIEW_RESOLVE_TRACK,
            track_ids=[1],
            input_payload={},
            max_attempts=3,
        )
        session.commit()

    reserved = items.reserve_next(worker_id="test-worker", worker_type=WORKER_TYPE_PREVIEW_RESOLVER)
    assert reserved is not None
    worker.process_item(reserved)

    with Session(engine) as session:
        from app.database.repositories.track_previews import TrackPreviewsRepository

        row = TrackPreviewsRepository().get_for_track_provider(
            session, track_id=1, provider="deezer"
        )
        assert row is not None
        assert row.is_available
