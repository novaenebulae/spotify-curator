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

    # Jobs / workers
    job_worker_heartbeat_interval_seconds: int = 10
    job_item_lock_timeout_seconds: int = 600
    job_events_enabled: bool = True
    worker_heartbeats_enabled: bool = True

    # Audio segments
    audio_segment_max_seconds: float = 30.0
    audio_keep_segments_after_analysis: bool = False
    audio_debug_keep_failed_segments: bool = False
    audio_download_workers: int = 2
    audio_download_concurrency: int = 2
    audio_download_max_retries: int = 3
    audio_download_batch_size: int = 20
    audio_download_item_lock_timeout_seconds: int = 600
    audio_segment_default_seconds: float = 15.0
    audio_segment_strategy: str = "hybrid_deezer_youtube_representative"

    # Deezer previews (metadata only for UI)
    deezer_api_base_url: str = "https://api.deezer.com"
    deezer_timeout_seconds: float = 15.0
    deezer_max_retries: int = 3
    deezer_preview_ui_min_confidence: float = 0.55
    deezer_preview_analysis_min_confidence: float = 0.70
    youtube_min_confidence: float = 0.50
    audio_preview_cache_metadata_days: int = 7
    audio_previews_enabled: bool = True

    # Hybrid confidence weights
    confidence_weight_youtube_representative: float = 0.95
    confidence_weight_youtube_fallback_three: float = 1.00
    confidence_weight_deezer_preview_only: float = 0.70

    # yt-dlp / ffmpeg
    ytdlp_format: str = "bestaudio/best"
    ytdlp_timeout_seconds: int = 120
    ffmpeg_timeout_seconds: int = 120
    ytdlp_duration_tolerance_seconds: int = 15

    # Essentia low-level
    essentia_lowlevel_workers: int = 2
    essentia_lowlevel_item_mode: str = "track"
    essentia_lowlevel_max_retries: int = 2
    essentia_lowlevel_profile: str = "/app/profiles/essentia_lowlevel_basic.yaml"
    essentia_lowlevel_pipeline_version: str = "essentia_lowlevel_v1"
    essentia_lowlevel_item_lock_timeout_seconds: int = 900
    essentia_lowlevel_image: str = "ghcr.io/mtg/essentia"
    essentia_lowlevel_image_tag: str = "bullseye-v2.1_beta5"
    essentia_lowlevel_timeout_seconds: int = 180

    audio_enrich_default_limit: int = 5000
    audio_enrich_max_limit: int = 10000


settings = Settings()
