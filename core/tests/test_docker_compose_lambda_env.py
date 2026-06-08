from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
LAMBDA_COMPOSE = REPO_ROOT / "docker-compose.lambda.yml"
LAMBDA_ENV_EXAMPLE = REPO_ROOT / ".env.lambda.example"
LAMBDA_ENV = REPO_ROOT / ".env.lambda"


@pytest.fixture(autouse=True)
def ensure_lambda_env_file() -> None:
    created = False
    if not LAMBDA_ENV.is_file() and LAMBDA_ENV_EXAMPLE.is_file():
        LAMBDA_ENV.write_text(LAMBDA_ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        created = True
    yield
    if created and LAMBDA_ENV.is_file():
        LAMBDA_ENV.unlink()


def _compose_cmd(*, profiles: tuple[str, ...] = ()) -> list[str]:
    cmd = [
        "docker",
        "compose",
        "-f",
        str(REPO_ROOT / "docker-compose.yml"),
        "-f",
        str(REPO_ROOT / "docker-compose.gpu.yml"),
        "-f",
        str(LAMBDA_COMPOSE),
        "--env-file",
        str(LAMBDA_ENV if LAMBDA_ENV.is_file() else LAMBDA_ENV_EXAMPLE),
    ]
    for profile in profiles:
        cmd.extend(["--profile", profile])
    cmd.extend(["config", "--format", "json"])
    return cmd


def test_lambda_compose_config_without_local_dotenv() -> None:
    """Lambda stack must not require a host .env (only .env.lambda on the instance)."""
    env = {k: v for k, v in os.environ.items() if k != "COMPOSE_FILE"}
    result = subprocess.run(
        _compose_cmd(),
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert ".env not found" not in result.stderr.lower()


def test_lambda_compose_core_api_gets_lambda_paths() -> None:
    result = subprocess.run(
        _compose_cmd(),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    doc = yaml.safe_load(result.stdout)
    services = doc.get("services") or {}
    core_env = services["core-api"]["environment"]
    assert core_env["APP_ENV"] == "lambda"
    assert core_env["CACHE_DIR"] == "/app/temp-audio"
    assert core_env["DATABASE_URL"] == "sqlite:////app/data/spotify_curator.sqlite"
    assert core_env["ESSENTIA_TF_DEVICE"] == "gpu"
    assert core_env["ESSENTIA_TF_WARMUP"] == "false"
    assert core_env["VITE_API_BASE_URL"] == "http://127.0.0.1:8000"


def test_lambda_overlay_replaces_env_file() -> None:
    text = LAMBDA_COMPOSE.read_text(encoding="utf-8")
    assert "env_file: !override" in text
    assert "- .env.lambda" in text


def test_lambda_tf_worker_memory_limits() -> None:
    result = subprocess.run(
        _compose_cmd(profiles=("advanced-analysis",)),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    doc = yaml.safe_load(result.stdout)
    tf = (doc.get("services") or {})["essentia-tensorflow-worker"]
    # docker compose config may normalize human-readable limits to bytes.
    assert tf["mem_limit"] in ("24g", "25769803776")
    assert tf["memswap_limit"] in ("24g", "25769803776")
    assert tf["shm_size"] in ("4gb", "4294967296")
