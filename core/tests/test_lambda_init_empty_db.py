from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "lambda" / "init-empty-db.sh"


def _bash_path(path: Path) -> str:
    resolved = path.resolve()
    if platform.system() == "Windows":
        drive = resolved.drive.rstrip(":").lower()
        tail = resolved.as_posix()[len(resolved.drive) :]
        return f"/{drive}{tail}"
    return str(resolved)


def _bash_available() -> bool:
    try:
        subprocess.run(["bash", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _can_run_lambda_shell_tests() -> bool:
    if platform.system() == "Windows":
        return False
    return _bash_available()


pytestmark = pytest.mark.skipif(
    not _can_run_lambda_shell_tests(),
    reason="init-empty-db.sh integration tests require Linux/bash (Lambda target)",
)


@pytest.fixture(autouse=True)
def ensure_lambda_env_file() -> None:
    env = REPO_ROOT / ".env.lambda"
    example = REPO_ROOT / ".env.lambda.example"
    created = False
    if not env.is_file() and example.is_file():
        env.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        created = True
    yield
    if created and env.is_file():
        env.unlink()


def _run_script(
    tmp_path: Path,
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["RUNTIME_ROOT"] = str(tmp_path / "runtime")
    env["SKIP_DOCKER_INIT"] = "1"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_init_empty_db_script_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--force" in text
    assert "--backup-existing" in text
    assert "init_db" in text
    assert "SKIP_DOCKER_INIT" in text
    assert "integrity_check" in text


def test_init_empty_db_refuses_existing_without_force(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    db_path = runtime / "data" / "spotify_curator.sqlite"
    db_path.parent.mkdir(parents=True)
    db_path.write_bytes(b"existing")

    result = _run_script(tmp_path)
    assert result.returncode == 1
    assert "already exists" in result.stderr.lower()


def test_init_empty_db_force_removes_existing(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    db_path = runtime / "data" / "spotify_curator.sqlite"
    db_path.parent.mkdir(parents=True)
    db_path.write_bytes(b"existing")

    result = _run_script(tmp_path, "--force")
    assert result.returncode == 0
    assert not db_path.exists()
    assert "skipping migration" in result.stdout.lower()


def test_init_empty_db_backup_existing(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    backup_dir = tmp_path / "backups"
    db_path = runtime / "data" / "spotify_curator.sqlite"
    db_path.parent.mkdir(parents=True)
    db_path.write_bytes(b"existing")

    result = _run_script(
        tmp_path,
        "--backup-existing",
        extra_env={"BACKUP_DIR": str(backup_dir)},
    )
    assert result.returncode == 0
    backups = list(backup_dir.glob("spotify_curator.*.sqlite"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"existing"
    assert not db_path.exists()
