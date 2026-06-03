from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.database.models_features import AudioFeature
from app.database.repositories.feature_sources import FeatureSourcesRepository
from app.audio.essentia_aggregate import aggregate_segment_features
from app.audio.essentia_parser import parse_essentia_json
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
    db_path = tmp_path / "track_features.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_library(session)
    return TestClient(create_app())


def _seed_reccobeats(session: Session, track_id: int) -> None:
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
    FeatureUpsertService().upsert_reccobeats(
        session,
        track_id=track_id,
        fetch_result=result,
        normalized=map_reccobeats_result(result),
    )


def _seed_essentia(session: Session, track_id: int, *, is_active: bool = True) -> None:
    sources = FeatureSourcesRepository()
    src = sources.get_by_name(session, "essentia_lowlevel")
    assert src is not None
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    row = AudioFeature(
        track_id=track_id,
        feature_source_id=src.id,
        bpm=127.0,
        key=7,
        mode=1,
        loudness=-8.2,
        feature_confidence=0.85,
        status="success",
        is_active=is_active,
        fetched_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    FeatureUpsertService()._features.insert_raw_payload(
        session,
        track_id=track_id,
        feature_source_id=src.id,
        request_key="essentia_lowlevel_v1",
        payload_json=json.dumps(
            {
                "pipeline_version": "essentia_lowlevel_v1",
                "segments_used": 2,
                "aggregated": {
                    "analysis_decision": "deezer_preview_plus_two_youtube_segments",
                    "spectral_centroid": 2100.5,
                    "dynamic_complexity": 4.2,
                },
            }
        ),
        status_code=200,
        fetched_at=now,
    )


def test_track_features_not_found(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/features/tracks/99999")
    assert res.status_code == 404


def test_track_features_empty(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    res = client.get("/api/v1/features/tracks/1")
    assert res.status_code == 200
    data = res.json()
    assert data["merged"] is None
    assert data["sources"] == []
    assert data["availability"]["has_any_features"] is False


def test_track_features_reccobeats_only(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    engine = get_engine()
    with Session(engine) as session:
        _seed_reccobeats(session, 1)
        session.commit()
    res = client.get("/api/v1/features/tracks/1")
    assert res.status_code == 200
    data = res.json()
    assert data["availability"]["has_reccobeats"] is True
    assert data["merged"]["primary_source"] == "reccobeats"
    assert data["merged"]["fields"]["bpm"] == SAMPLE_FEATURES["tempo"]
    assert data["merged"]["fields"]["energy"] is not None


def test_track_features_both_sources_essentia_wins_merge(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    engine = get_engine()
    with Session(engine) as session:
        _seed_reccobeats(session, 1)
        _seed_essentia(session, 1, is_active=True)
        rb_src = FeatureSourcesRepository().get_by_name(session, "reccobeats")
        assert rb_src is not None
        from sqlalchemy import select

        rb_row = session.execute(
            select(AudioFeature).where(
                AudioFeature.track_id == 1,
                AudioFeature.feature_source_id == rb_src.id,
            )
        ).scalar_one()
        rb_row.is_active = False
        session.commit()
    res = client.get("/api/v1/features/tracks/1")
    data = res.json()
    assert len(data["sources"]) == 2
    assert data["merged"]["primary_source"] == "essentia_lowlevel"
    assert data["merged"]["meta"]["segments_used"] == 2
    ess = next(s for s in data["sources"] if s["source_name"] == "essentia_lowlevel")
    assert ess["extended"].get("spectral_centroid") == 2100.5
    rb = next(s for s in data["sources"] if s["source_name"] == "reccobeats")
    assert rb["is_active"] is False
    assert rb["fields"].get("energy") is not None


def test_track_features_essentia_extended_via_upsert_path(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    fixture = Path(__file__).parent / "fixtures" / "essentia_lowlevel_sample.json"
    parsed = parse_essentia_json(json.loads(fixture.read_text(encoding="utf-8")))
    aggregated = aggregate_segment_features([parsed], analysis_decision="deezer_only")
    engine = get_engine()
    with Session(engine) as session:
        FeatureUpsertService().upsert_essentia_lowlevel(
            session,
            track_id=1,
            aggregated=aggregated,
            force_refresh=True,
        )
        session.commit()
    res = client.get("/api/v1/features/tracks/1")
    assert res.status_code == 200
    data = res.json()
    ess = next(s for s in data["sources"] if s["source_name"] == "essentia_lowlevel")
    ext = ess["extended"]
    assert ext.get("spectral_centroid") == 2200.0
    assert ext.get("spectral_rolloff") == 4500.0
    assert ext.get("dynamic_complexity") == 4.5
    assert ext.get("onset_rate") == 2.1
    assert len(ext.get("mfcc") or []) == 5
    assert len(ext.get("hpcp") or []) == 3
    assert ext.get("spectral_contrast") == [1.0, 2.0, 3.0]
