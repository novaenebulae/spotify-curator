from pathlib import Path
from unittest.mock import patch

from app.database.url import (
    DOCKER_DATABASE_URL,
    is_windows_sqlite_url,
    resolve_database_url,
)


def test_is_windows_sqlite_url_detects_drive_paths() -> None:
    assert is_windows_sqlite_url("sqlite:///c:/Users/x/data.sqlite")
    assert is_windows_sqlite_url("sqlite:///C:/data.sqlite")
    assert not is_windows_sqlite_url("sqlite:////app/data/spotify_curator.sqlite")
    assert not is_windows_sqlite_url("sqlite:///./data/test.sqlite")


def test_resolve_database_url_uses_env_on_host(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite:///c:/Users/Lucas/Desktop/spotify-curator/data/spotify_curator.sqlite",
    )
    with patch("app.database.url.running_in_docker", return_value=False):
        assert (
            resolve_database_url()
            == "sqlite:///c:/Users/Lucas/Desktop/spotify-curator/data/spotify_curator.sqlite"
        )


def test_resolve_database_url_ignores_windows_path_in_docker(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite:///c:/Users/Lucas/Desktop/spotify-curator/data/spotify_curator.sqlite",
    )
    with patch("app.database.url.running_in_docker", return_value=True):
        assert resolve_database_url() == DOCKER_DATABASE_URL


def test_compose_file_pins_database_url() -> None:
    compose = (
        Path(__file__).resolve().parents[2] / "docker-compose.yml"
    ).read_text(encoding="utf-8")
    assert "DATABASE_URL=sqlite:////app/data/spotify_curator.sqlite" in compose
    assert "${DATABASE_URL" not in compose
