from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_audio import AudioDownloadJob
from app.database.repositories.track_previews import TrackPreviewsRepository
from app.features.reccobeats_mapper import NormalizedFeatureRow
from app.features.upsert import FeatureUpsertService
from app.main import create_app
from app.reccobeats.schemas import ReccoBeatsFetchResult
from tests.fixtures.library_seed import seed_library


def test_failures_union_and_failures_after(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "fail_insights.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    now = datetime.utcnow()
    old = now - timedelta(days=2)
    with Session(engine) as session:
        seed = seed_library(session)
        track_id = int(seed["sp_t2"])
        upsert = FeatureUpsertService()
        upsert.upsert_reccobeats(
            session,
            track_id=track_id,
            fetch_result=ReccoBeatsFetchResult(track=None, features=None),
            normalized=NormalizedFeatureRow(
                status="failed",
                error_code="ERR",
                error_message="RB fail",
            ),
            replace_failed=True,
        )
        TrackPreviewsRepository().upsert(
            session,
            track_id=track_id,
            provider="deezer",
            fields={
                "is_available": False,
                "last_error": "No preview",
                "updated_at": now,
            },
        )
        session.add(
            AudioDownloadJob(
                track_id=track_id,
                provider="ytdlp",
                status="failed",
                last_error="download fail",
                result_json="{}",
                created_at=old,
                finished_at=old,
            )
        )
        session.commit()

    client = TestClient(create_app())
    res = client.get("/api/v1/features/coverage", params={"include_failed": True})
    assert res.status_code == 200
    items = res.json()["failures"]["items"]
    sources = {i["source"] for i in items}
    assert "reccobeats" in sources
    assert "deezer_preview" in sources
    assert "audio_download" in sources
    assert items[0].get("occurred_at")

    cleared = (now - timedelta(hours=1)).isoformat()
    res2 = client.get(
        "/api/v1/features/coverage",
        params={"include_failed": True, "failures_after": cleared},
    )
    filtered = res2.json()["failures"]["items"]
    assert all(i["source"] != "audio_download" for i in filtered)
