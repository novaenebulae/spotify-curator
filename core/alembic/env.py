from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.database.models import Base
from app.database.models_jobs import Job  # noqa: F401
from app.database.models_library import (  # noqa: F401
    Album,
    Artist,
    ExternalId,
    LikedTrack,
    SpotifyAlbum,
    SpotifyArtist,
    SpotifyTrack,
    Track,
    TrackArtist,
)
from app.database.models_library_actions import LibraryAction  # noqa: F401
from app.database.models_oauth import OAuthPkceState  # noqa: F401
from app.database.models_playlists import Playlist, PlaylistTrack  # noqa: F401
from app.database.models_runtime import DockerRuntimeCheck  # noqa: F401
from app.database.models_snapshots import (  # noqa: F401
    LikedTrackSnapshot,
    PlaylistSnapshot,
    PlaylistTrackSnapshot,
    Snapshot,
)
from app.database.models_spotify_auth import SpotifyAuthToken  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def get_url() -> str:
    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return configured
    return os.getenv("DATABASE_URL", "sqlite:////app/data/spotify_curator.sqlite")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
