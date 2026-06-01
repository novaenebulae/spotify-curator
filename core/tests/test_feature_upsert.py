from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from alembic import command
from app.database.engine import get_engine, reset_engine
from app.database.models_features import AudioFeature, AudioFeatureRawPayload
from app.database.models_library import ExternalId
from app.features.reccobeats_mapper import map_reccobeats_result
from app.features.upsert import FeatureUpsertService
from app.reccobeats.schemas import (
    ReccoBeatsArtist,
    ReccoBeatsAudioFeatures,
    ReccoBeatsFetchResult,
    ReccoBeatsTrackMeta,
)
from tests.fixtures.library_seed import seed_library
from tests.fixtures.reccobeats_responses import RECCOBEATS_TRACK_ID, SAMPLE_FEATURES, SAMPLE_TRACK


def _alembic_cfg(db_path: Path) -> Config:
    core_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(core_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(core_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    return cfg


@pytest.fixture()
def feature_db(tmp_path, monkeypatch):
    db_path = tmp_path / "features.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    command.upgrade(_alembic_cfg(db_path), "head")
    engine = get_engine()
    with Session(engine) as session:
        seed = seed_library(session)
        session.commit()
    yield engine, seed


def _success_result() -> ReccoBeatsFetchResult:
    track = ReccoBeatsTrackMeta(
        id=RECCOBEATS_TRACK_ID,
        track_title=SAMPLE_TRACK["trackTitle"],
        artists=[ReccoBeatsArtist(id="a1", name="Taylor Swift")],
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
    return ReccoBeatsFetchResult(
        track=track,
        features=features,
        track_raw=SAMPLE_TRACK,
        features_raw=SAMPLE_FEATURES,
        features_status_code=200,
    )


def test_upsert_stores_raw_and_features(feature_db) -> None:
    engine, seed = feature_db
    track_id = int(seed["sp_t1"])
    svc = FeatureUpsertService()
    result = _success_result()
    normalized = map_reccobeats_result(result, local_isrc=SAMPLE_TRACK["isrc"])

    with Session(engine) as session:
        feature_id, _ = svc.upsert_reccobeats(
            session,
            track_id=track_id,
            fetch_result=result,
            normalized=normalized,
        )
        session.commit()

        raw_count = session.execute(
            select(func.count()).select_from(AudioFeatureRawPayload)
        ).scalar_one()
        active = session.execute(
            select(AudioFeature).where(AudioFeature.id == feature_id)
        ).scalar_one()
        ext = session.execute(
            select(ExternalId).where(
                ExternalId.track_id == track_id,
                ExternalId.id_type == "reccobeats_id",
            )
        ).scalar_one_or_none()

    assert raw_count == 1
    assert active.status == "success"
    assert active.bpm == 93.5
    assert ext is not None
    assert ext.id_value == RECCOBEATS_TRACK_ID


def test_upsert_idempotent_skips_duplicate_active(feature_db) -> None:
    engine, seed = feature_db
    track_id = int(seed["sp_t1"])
    svc = FeatureUpsertService()
    result = _success_result()
    normalized = map_reccobeats_result(result)

    with Session(engine) as session:
        first_id, _ = svc.upsert_reccobeats(
            session,
            track_id=track_id,
            fetch_result=result,
            normalized=normalized,
        )
        second_id, applied = svc.upsert_reccobeats(
            session,
            track_id=track_id,
            fetch_result=result,
            normalized=normalized,
        )
        session.commit()
        active_count = session.execute(
            select(func.count())
            .select_from(AudioFeature)
            .where(AudioFeature.track_id == track_id, AudioFeature.is_active.is_(True))
        ).scalar_one()
        raw_count = session.execute(
            select(func.count()).select_from(AudioFeatureRawPayload)
        ).scalar_one()

    assert first_id == second_id
    assert applied is False
    assert active_count == 1
    assert raw_count == 2


def test_force_refresh_deactivates_old(feature_db) -> None:
    engine, seed = feature_db
    track_id = int(seed["sp_t1"])
    svc = FeatureUpsertService()
    result = _success_result()
    normalized = map_reccobeats_result(result)

    with Session(engine) as session:
        svc.upsert_reccobeats(
            session,
            track_id=track_id,
            fetch_result=result,
            normalized=normalized,
        )
        normalized2 = map_reccobeats_result(result)
        normalized2_dict = normalized2.to_column_dict()
        normalized2_dict["bpm"] = 100.0
        from app.features.reccobeats_mapper import NormalizedFeatureRow

        normalized2 = NormalizedFeatureRow(**{**normalized2.__dict__, "bpm": 100.0})
        second_id, _ = svc.upsert_reccobeats(
            session,
            track_id=track_id,
            fetch_result=result,
            normalized=normalized2,
            force_refresh=True,
        )
        session.commit()
        rows = session.execute(
            select(AudioFeature).where(AudioFeature.track_id == track_id).order_by(AudioFeature.id)
        ).scalars().all()

    assert len(rows) == 2
    assert rows[0].is_active is False
    assert rows[1].id == second_id
    assert rows[1].is_active is True
    assert rows[1].bpm == 100.0
