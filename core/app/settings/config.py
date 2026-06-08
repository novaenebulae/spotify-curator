from __future__ import annotations

from pydantic import Field, model_validator
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
    deezer_preview_ui_min_confidence: float = 0.60
    # Kept for API/runtime visibility; analysis uses track_previews.is_available (resolver gate).
    deezer_preview_analysis_min_confidence: float = 0.60
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
    audio_analysis_pipeline_version: str = "audio_pipeline_v1"
    analysis_pipeline_mode: str = "streaming"
    analysis_pipeline_tick_interval_seconds: int = 45
    analysis_pipeline_tick_enabled: bool = True
    audio_cleanup_wait_for_all_consumers: bool = True
    essentia_lowlevel_item_lock_timeout_seconds: int = 900
    essentia_lowlevel_image: str = "ghcr.io/mtg/essentia"
    essentia_lowlevel_image_tag: str = "bullseye-v2.1_beta5"
    essentia_lowlevel_timeout_seconds: int = 180

    # Essentia TensorFlow (phase 6.4)
    analysis_advanced_enabled: bool = True
    analysis_default_include_tensorflow: bool = True
    essentia_tensorflow_workers: int = 1
    essentia_tensorflow_batch_size: int = 1
    essentia_tensorflow_max_retries: int = 1
    essentia_tensorflow_item_lock_timeout_seconds: int = 1800
    essentia_tensorflow_status_only: bool = False
    essentia_tensorflow_pipeline_version: str = "essentia_tensorflow_v1"
    essentia_tensorflow_image: str = "ghcr.io/mtg/essentia"
    essentia_tensorflow_image_tag: str = "bullseye-v2.1_beta5"
    model_registry_path: str = "/app/models/model_registry.json"
    model_hash_check_enabled: bool = True
    model_download_enabled: bool = False

    # Runtime environment marker (controls stub guard, see phase 6.8B)
    app_env: str = "development"
    run_env: str = "local"

    # Lambda / cloud paths (optional overrides)
    sqlite_path: str | None = None
    temp_audio_dir: str | None = None

    # Essentia TensorFlow real inference (phase 6.8B)
    essentia_tf_real_inference_enabled: bool = True
    essentia_tf_allow_stubs_in_tests: bool = False
    essentia_tf_require_models_for_advanced: bool = False
    essentia_tf_fail_on_stub_in_production: bool = True
    essentia_tf_pipeline_version: str = "phase6_tf_unified_v1"
    essentia_model_profile: str | None = None
    essentia_tf_warmup: bool = False
    essentia_tf_device: str = "auto"
    essentia_tf_batch_size: int = 1
    essentia_tf_batch_timeout_ms: int = 1000

    # Essentia TensorFlow model management (phase 6.8A)
    essentia_models_dir: str = "/app/models/essentia"
    essentia_models_manifest: str = "/app/core/app/models_registry/essentia_models_manifest.yaml"
    essentia_models_default_profile: str = "phase6-recommended"
    essentia_models_download_timeout_seconds: int = 300
    essentia_models_verify_hash: bool = True
    essentia_models_accept_license: bool = False
    advanced_features_top_k_genres: int = 10
    energy_proxy_enabled: bool = True

    audio_enrich_default_limit: int = 5000
    audio_enrich_max_limit: int = 10000

    preview_resolver_workers: int = 2

    @model_validator(mode="after")
    def _apply_path_aliases(self) -> Settings:
        if self.sqlite_path:
            path = self.sqlite_path.replace("\\", "/")
            if not path.startswith("/"):
                path = f"/{path}"
            object.__setattr__(self, "database_url", f"sqlite:///{path}")
        if self.temp_audio_dir:
            object.__setattr__(self, "cache_dir", self.temp_audio_dir)
        return self

    @property
    def effective_essentia_model_profile(self) -> str:
        return self.essentia_model_profile or self.essentia_models_default_profile

    @property
    def effective_essentia_tf_batch_size(self) -> int:
        """Inference micro-batch alias; falls back to pipeline refresh batch size."""
        if self.essentia_tf_batch_size > 1:
            return self.essentia_tf_batch_size
        return self.essentia_tensorflow_batch_size


settings = Settings()
