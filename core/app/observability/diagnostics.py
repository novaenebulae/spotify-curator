from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.engine import get_engine
from app.database.models_runtime import DockerRuntimeCheck
from app.database.repositories.docker_checks import DockerChecksRepository
from app.settings.config import settings

_STDIO_MAX = 8192


@dataclass(frozen=True)
class CheckResult:
    check_name: str
    command: str
    exit_code: int | None
    stdout: str | None
    stderr: str | None
    success: bool
    service_name: str | None = None
    image_name: str | None = None
    image_tag: str | None = None


def _truncate(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= _STDIO_MAX:
        return value
    return value[:_STDIO_MAX] + "\n... [truncated]"


def _run_command(command: list[str]) -> CheckResult:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return CheckResult(
            check_name=command[0],
            command=" ".join(command),
            exit_code=proc.returncode,
            stdout=_truncate(proc.stdout),
            stderr=_truncate(proc.stderr),
            success=proc.returncode == 0,
        )
    except FileNotFoundError as e:
        return CheckResult(
            check_name=command[0],
            command=" ".join(command),
            exit_code=None,
            stdout=None,
            stderr=str(e),
            success=False,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            check_name=command[0],
            command=" ".join(command),
            exit_code=None,
            stdout=None,
            stderr="Command timed out",
            success=False,
        )


def _path_status(path_str: str, check_name: str) -> CheckResult:
    path = Path(path_str)
    exists = path.exists()
    writable = os.access(path, os.W_OK) if exists else False
    success = exists and path.is_dir() and writable
    return CheckResult(
        check_name=check_name,
        command=f"path:{path}",
        exit_code=0 if success else 1,
        stdout=f"exists={exists} is_dir={path.is_dir()} writable={writable}",
        stderr=None if success else f"Path not ready: {path}",
        success=success,
    )


def run_docker_checks() -> list[CheckResult]:
    results: list[CheckResult] = []

    docker_bin = shutil.which("docker")
    if docker_bin:
        proc = _run_command([docker_bin, "version"])
        results.append(
            CheckResult(
                check_name="docker_available",
                command=proc.command,
                exit_code=proc.exit_code,
                stdout=proc.stdout,
                stderr=proc.stderr,
                success=proc.success,
            )
        )
    else:
        results.append(
            CheckResult(
                check_name="docker_available",
                command="docker version",
                exit_code=None,
                stdout=None,
                stderr="docker not found in PATH",
                success=False,
            )
        )

    compose_bin = shutil.which("docker")
    if compose_bin:
        proc = _run_command([compose_bin, "compose", "version", "--short"])
        results.append(
            CheckResult(
                check_name="compose_available",
                command=proc.command,
                exit_code=proc.exit_code,
                stdout=proc.stdout,
                stderr=proc.stderr,
                success=proc.success,
            )
        )
    else:
        results.append(
            CheckResult(
                check_name="compose_available",
                command="docker compose version",
                exit_code=None,
                stdout=None,
                stderr="docker compose not available",
                success=False,
            )
        )

    results.append(_path_status(settings.data_dir, "volume_data"))
    results.append(_path_status(settings.cache_dir, "volume_cache"))
    results.append(_path_status(settings.export_dir, "volume_exports"))

    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        results.append(
            CheckResult(
                check_name="sqlite_writable",
                command="SELECT 1",
                exit_code=0,
                stdout="ok",
                stderr=None,
                success=True,
            )
        )
    except Exception as e:  # noqa: BLE001
        results.append(
            CheckResult(
                check_name="sqlite_writable",
                command="SELECT 1",
                exit_code=1,
                stdout=None,
                stderr=str(e),
                success=False,
            )
        )

    return results


def persist_checks(results: list[CheckResult]) -> list[dict]:
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    engine = get_engine()
    out: list[dict] = []

    with Session(engine) as session:
        rows: list[DockerRuntimeCheck] = []
        for res in results:
            row = DockerRuntimeCheck(
                id=str(uuid.uuid4()),
                check_name=res.check_name,
                service_name=res.service_name,
                image_name=res.image_name,
                image_tag=res.image_tag,
                command=res.command,
                exit_code=res.exit_code,
                stdout=res.stdout,
                stderr=res.stderr,
                success=res.success,
                created_at=now,
            )
            session.add(row)
            rows.append(row)
        session.commit()
        for row in rows:
            session.refresh(row)
            out.append(_row_to_dict(row))
    return out


def list_recent_checks(*, limit: int = 50) -> list[dict]:
    repo = DockerChecksRepository()
    engine = get_engine()
    with Session(engine) as session:
        rows = repo.list_recent(session, limit=limit)
        return [_row_to_dict(r) for r in rows]


def legacy_diagnostics_payload() -> dict:
    return {
        "env": {
            "database_url_set": bool(os.getenv("DATABASE_URL")),
            "cache_dir": settings.cache_dir,
            "models_dir": settings.models_dir,
            "logs_dir": settings.logs_dir,
            "export_dir": settings.export_dir,
            "api_version": settings.app_version,
        },
        "paths": {
            "data": _path_dict(settings.data_dir),
            "cache": _path_dict(settings.cache_dir),
            "models": _path_dict(settings.models_dir),
            "logs": _path_dict(settings.logs_dir),
            "exports": _path_dict(settings.export_dir),
        },
        "recent_docker_checks": list_recent_checks(limit=10),
    }


def _path_dict(path_str: str) -> dict:
    p = Path(path_str)
    return {
        "path": str(p),
        "exists": p.exists(),
        "is_dir": p.is_dir(),
        "writable": os.access(p, os.W_OK) if p.exists() else False,
    }


def _row_to_dict(row: DockerRuntimeCheck) -> dict:
    return {
        "id": row.id,
        "check_name": row.check_name,
        "service_name": row.service_name,
        "image_name": row.image_name,
        "image_tag": row.image_tag,
        "command": row.command,
        "exit_code": row.exit_code,
        "stdout": row.stdout,
        "stderr": row.stderr,
        "success": row.success,
        "created_at": row.created_at.isoformat(),
    }
