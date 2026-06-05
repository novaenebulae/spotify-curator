from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"

SERVICES_WITH_ENV_FILE = (
    "core-api",
    "audio-downloader",
    "preview-resolver-worker",
    "essentia-lowlevel-worker",
    "essentia-tensorflow-worker",
)

CRITICAL_ENV_KEYS = (
    "ANALYSIS_PIPELINE_TICK_ENABLED",
    "ESSENTIA_TENSORFLOW_BATCH_SIZE",
    "ESSENTIA_TENSORFLOW_ITEM_LOCK_TIMEOUT_SECONDS",
    "ESSENTIA_TF_PIPELINE_VERSION",
    "ESSENTIA_LOWLEVEL_PIPELINE_VERSION",
    "ESSENTIA_LOWLEVEL_PROFILE",
)


def _load_compose() -> dict:
    with COMPOSE_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_compose_services_use_env_file() -> None:
    doc = _load_compose()
    services = doc.get("services") or {}
    for name in SERVICES_WITH_ENV_FILE:
        assert name in services, f"missing service {name}"
        env_file = services[name].get("env_file")
        assert env_file == [".env"], f"{name} must use env_file: .env"


def test_compose_shared_env_includes_analysis_vars() -> None:
    doc = _load_compose()
    app_env = doc.get("x-app-env") or {}
    for key in CRITICAL_ENV_KEYS:
        assert key in app_env, f"x-app-env missing {key}"


def test_compose_tensorflow_worker_has_memory_limits() -> None:
    doc = _load_compose()
    tf = doc["services"]["essentia-tensorflow-worker"]
    assert tf.get("mem_limit")
    assert tf.get("memswap_limit")
    assert tf.get("cpus")


def test_compose_core_api_has_memory_limit() -> None:
    doc = _load_compose()
    api = doc["services"]["core-api"]
    assert api.get("mem_limit") == "768m"
