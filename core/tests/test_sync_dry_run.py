from __future__ import annotations
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.init_db import init_db
from app.main import create_app
from app.playlists.presets import load_presets
from tests.fixtures.library_seed import seed_library
from tests.test_track_features_api import _seed_reccobeats


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "sync.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        ids = seed_library(session)
        _seed_reccobeats(session, int(ids["sp_t1"]))
        session.commit()
    return TestClient(create_app())


def test_sync_dry_run_no_spotify_write(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    preview = client.post(
        "/api/v1/generated-playlists/preview",
        json={"rule": load_presets()[0]["rule"]},
    )
    gp_id = preview.json()["generated_playlist_id"]

    mock_client = MagicMock()
    mock_client.iter_playlist_items.return_value = [
        {"track": {"id": "sp_t1"}},
    ]

    with patch("app.playlists.sync_dry_run.SpotifyClient", return_value=mock_client):
        with patch("app.playlists.sync_dry_run.SpotifyTokenStore") as store_cls:
            store = store_cls.return_value
            store.load.return_value = MagicMock(scope="user-read-private")
            resp = client.post(
                "/api/v1/sync/dry-run",
                json={
                    "generated_playlist_id": gp_id,
                    "target_spotify_playlist_id": "target_pl",
                    "sync_mode": "replace",
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["dry_run"] is True
    assert "diff" in body
    mock_client.iter_playlist_items.assert_called_once()
    assert not hasattr(mock_client, "add_tracks_to_playlist") or not mock_client.add_tracks_to_playlist.called
