from __future__ import annotations

from app.settings.config import Settings


def test_sqlite_path_overrides_database_url(monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", "/app/data/custom.sqlite")
    s = Settings()
    assert s.database_url == "sqlite:////app/data/custom.sqlite"


def test_temp_audio_dir_overrides_cache_dir(monkeypatch) -> None:
    monkeypatch.setenv("TEMP_AUDIO_DIR", "/app/temp-audio")
    s = Settings()
    assert s.cache_dir == "/app/temp-audio"


def test_essentia_model_profile_alias(monkeypatch) -> None:
    monkeypatch.setenv("ESSENTIA_MODEL_PROFILE", "phase6-minimal")
    monkeypatch.setenv("ESSENTIA_MODELS_DEFAULT_PROFILE", "phase6-recommended")
    s = Settings()
    assert s.effective_essentia_model_profile == "phase6-minimal"


def test_lambda_env_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "lambda")
    monkeypatch.setenv("RUN_ENV", "lambda")
    monkeypatch.setenv("ESSENTIA_TF_WARMUP", "true")
    monkeypatch.setenv("ESSENTIA_TF_DEVICE", "gpu")
    s = Settings()
    assert s.app_env == "lambda"
    assert s.run_env == "lambda"
    assert s.essentia_tf_warmup is True
    assert s.essentia_tf_device == "gpu"
