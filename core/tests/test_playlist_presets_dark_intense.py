from __future__ import annotations

import os
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.playlists.feature_resolver import FeatureResolver
from app.playlists.presets import load_presets
from app.playlists.preview_service import PlaylistPreviewService
from app.playlists.rule_schemas import PlaylistRule
from tests.fixtures.library_seed import seed_library
from tests.test_track_features_api import _seed_reccobeats


def test_resolver_exposes_feature_confidence(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "fc.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        ids = seed_library(session)
        _seed_reccobeats(session, int(ids["sp_t1"]))
        session.commit()
        views = FeatureResolver().load_views(session, [int(ids["sp_t1"])])
    fc = views[int(ids["sp_t1"])].features.get("feature_confidence")
    assert fc is not None
    assert fc.status == "available"
    assert fc.value is not None
    assert float(fc.value) >= 0.35


def test_dark_intense_preset_selects_tracks(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "dark.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        ids = seed_library(session)
        for key in ("sp_t1", "sp_t2"):
            _seed_reccobeats(session, int(ids[key]))
        session.commit()

    preset = next(p for p in load_presets() if p["id"] == "dark_intense")
    rule = PlaylistRule.model_validate(preset["rule"])
    with Session(engine) as session:
        result = PlaylistPreviewService().generate_preview(session, rule)

    assert result["summary"]["selected_count"] >= 1
    assert result["summary"]["candidate_count"] >= 1
