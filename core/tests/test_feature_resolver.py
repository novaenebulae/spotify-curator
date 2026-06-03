from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.playlists.feature_resolver import FeatureResolver
from tests.fixtures.library_seed import seed_library
from tests.test_track_features_api import _seed_reccobeats


def _db(tmp_path, monkeypatch):
    db_path = tmp_path / "resolver.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        ids = seed_library(session)
        track_id = int(ids["sp_t1"])
        _seed_reccobeats(session, track_id)
        session.commit()
    return engine, track_id


def test_resolver_returns_track_feature_view(tmp_path, monkeypatch) -> None:
    engine, track_id = _db(tmp_path, monkeypatch)
    resolver = FeatureResolver()
    with Session(engine) as session:
        views = resolver.load_views(session, [track_id])
    assert track_id in views
    view = views[track_id]
    assert view.title == "Track One"
    energy = view.features.get("energy")
    assert energy is not None
    assert energy.status == "available"
    assert energy.value is not None


def test_resolver_future_feature_not_available_yet(tmp_path, monkeypatch) -> None:
    engine, track_id = _db(tmp_path, monkeypatch)
    resolver = FeatureResolver()
    with Session(engine) as session:
        views = resolver.load_views(session, [track_id])
    mood = views[track_id].features.get("mood_dark_score")
    assert mood is not None
    assert mood.status == "not_available_yet"
    assert mood.missing_reason == "FEATURE_NOT_AVAILABLE_YET"
