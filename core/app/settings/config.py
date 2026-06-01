from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"
    core_host: str = "127.0.0.1"
    core_port: int = 8765

    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:////app/data/spotify_curator.sqlite"
    data_dir: str = "/app/data"
    cache_dir: str = "/app/cache"
    models_dir: str = "/app/models"
    logs_dir: str = "/app/logs"

    spotify_client_id: str = ""
    spotify_redirect_uri: str = "http://127.0.0.1:8765/api/v1/spotify/auth/callback"
    spotify_scopes: str = (
        "user-read-private user-library-read playlist-read-private playlist-read-collaborative"
    )

    export_dir: str = "/app/exports"
    job_default_max_attempts: int = 3

    reccobeats_base_url: str = "https://api.reccobeats.com"
    reccobeats_timeout_seconds: float = 15.0
    reccobeats_max_retries: int = 3
    reccobeats_batch_delay_ms: int = 100
    reccobeats_http_batch_size: int = Field(default=40, ge=1, le=40)
    reccobeats_db_upsert_batch_size: int = 50
    reccobeats_enrich_default_limit: int = 5000
    reccobeats_enrich_max_limit: int = 10000


settings = Settings()
