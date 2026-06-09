from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, inspect, pool, text

from alembic import context
from app.database.models import Base
from app.database.url import resolve_database_url
from app.database.models_advanced_features import TrackAdvancedFeature  # noqa: F401
from app.database.models_track_embeddings import TrackEmbedding  # noqa: F401
from app.database.models_features import (  # noqa: F401
    AudioFeature,
    AudioFeatureRawPayload,
    FeatureSource,
)
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
from app.database.models_audio import (  # noqa: F401
    AudioAnalysisJob,
    AudioDownloadJob,
    TrackSegment,
)
from app.database.models_job_items import JobEvent, JobItem, WorkerHeartbeat  # noqa: F401
from app.database.models_previews import TrackPreview  # noqa: F401
from app.database.models_spotify_auth import SpotifyAuthToken  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve DB URL: DATABASE_URL wins; ignore alembic.ini template placeholders."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return resolve_database_url()
    configured = config.get_main_option("sqlalchemy.url")
    if configured and not configured.startswith("driver://"):
        return configured
    return "sqlite:////app/data/spotify_curator.sqlite"


def _render_as_batch(url: str) -> bool:
    return url.startswith("sqlite")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_render_as_batch(url),
    )

    with context.begin_transaction():
        context.run_migrations()


def _ensure_alembic_version_width(connection) -> None:
    """Revision ids exceed Alembic's default version_num VARCHAR(32) on PostgreSQL."""
    if connection.dialect.name != "postgresql":
        return
    if "alembic_version" not in inspect(connection).get_table_names():
        return
    connection.execute(
        text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")
    )


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    url = get_url()
    with connectable.connect() as connection:
        _ensure_alembic_version_width(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=_render_as_batch(url),
        )

        with context.begin_transaction():
            context.run_migrations()
        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
