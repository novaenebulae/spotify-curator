from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.features.reccobeats_mapper import map_reccobeats_result
from app.features.upsert import FeatureUpsertService
from app.main import create_app
from app.reccobeats.schemas import (
    ReccoBeatsArtist,
    ReccoBeatsAudioFeatures,
    ReccoBeatsFetchResult,
    ReccoBeatsTrackMeta,
)
from tests.fixtures.library_seed import seed_library
from tests.fixtures.reccobeats_responses import RECCOBEATS_TRACK_ID, SAMPLE_FEATURES, SAMPLE_TRACK


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "coverage.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
    return TestClient(create_app())


def _seed_success_feature(session: Session, track_id: int) -> None:
    track = ReccoBeatsTrackMeta(
        id=RECCOBEATS_TRACK_ID,
        track_title=SAMPLE_TRACK["trackTitle"],
        artists=[ReccoBeatsArtist(id="a1", name="Artist X")],
        duration_ms=SAMPLE_TRACK["durationMs"],
        isrc=SAMPLE_TRACK["isrc"],
        href=SAMPLE_TRACK["href"],
    )
    features = ReccoBeatsAudioFeatures(
        tempo=SAMPLE_FEATURES["tempo"],
        energy=SAMPLE_FEATURES["energy"],
        danceability=SAMPLE_FEATURES["danceability"],
        valence=SAMPLE_FEATURES["valence"],
        acousticness=SAMPLE_FEATURES["acousticness"],
        instrumentalness=SAMPLE_FEATURES["instrumentalness"],
        speechiness=SAMPLE_FEATURES["speechiness"],
        liveness=SAMPLE_FEATURES["liveness"],
        loudness=SAMPLE_FEATURES["loudness"],
        key=SAMPLE_FEATURES["key"],
        mode=SAMPLE_FEATURES["mode"],
        time_signature=SAMPLE_FEATURES["timeSignature"],
        duration_ms=SAMPLE_FEATURES["durationMs"],
    )
    result = ReccoBeatsFetchResult(
        track=track,
        features=features,
        track_raw=SAMPLE_TRACK,
        features_raw=SAMPLE_FEATURES,
    )
    upsert = FeatureUpsertService()
    upsert.upsert_reccobeats(
        session,
        track_id=track_id,
        fetch_result=result,
        normalized=map_reccobeats_result(result),
    )


def test_coverage_empty_library(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "cov_empty.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    client = TestClient(create_app())

    res = client.get("/api/v1/features/coverage")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["track_count"] == 0
    assert data["summary"]["coverage_percent"] == 0.0


def test_coverage_with_features(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "cov_feat.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed = seed_library(session)
        _seed_success_feature(session, int(seed["sp_t1"]))
        session.commit()

    client = TestClient(create_app())
    res = client.get("/api/v1/features/coverage", params={"include_fields": True})
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["track_count"] == 4
    assert data["summary"]["with_reccobeats"] == 1
    assert data["summary"]["missing_reccobeats"] == 3
    assert data["fields"]
    assert any(f["field"] == "bpm" and f["available_count"] == 1 for f in data["fields"])


def test_coverage_recent_failures(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "cov_fail.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed = seed_library(session)
        from app.features.reccobeats_mapper import NormalizedFeatureRow
        from app.reccobeats.schemas import ReccoBeatsFetchResult

        upsert = FeatureUpsertService()
        upsert.upsert_reccobeats(
            session,
            track_id=int(seed["sp_t2"]),
            fetch_result=ReccoBeatsFetchResult(track=None, features=None),
            normalized=NormalizedFeatureRow(
                status="failed",
                error_code="RECCOBEATS_HTTP_ERROR",
                error_message="HTTP 500",
            ),
            replace_failed=True,
        )
        session.commit()

    client = TestClient(create_app())
    res = client.get("/api/v1/features/coverage", params={"include_failed": True})
    assert res.status_code == 200
    failures = res.json()["recent_failures"]
    assert len(failures) >= 1
    assert failures[0]["status"] == "failed"
    assert failures[0]["title"] == "Track Two"
