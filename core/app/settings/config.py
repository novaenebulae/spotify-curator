from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    core_host: str = "127.0.0.1"
    core_port: int = 8765

    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:////app/data/spotify_curator.sqlite"

    spotify_client_id: str = ""
    spotify_redirect_uri: str = "http://127.0.0.1:8765/api/v1/spotify/auth/callback"
    spotify_scopes: str = (
        "user-read-private user-library-read playlist-read-private playlist-read-collaborative"
    )

    export_dir: str = "/app/exports"


settings = Settings()
