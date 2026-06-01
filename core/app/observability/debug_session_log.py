"""NDJSON debug logging for Cursor debug sessions (no secrets)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.settings.config import settings

_SESSION_ID = "a86d8d"
_LOG_NAMES = ("debug-a86d8d.log",)


def _log_paths() -> list[Path]:
    paths: list[Path] = [Path(settings.data_dir) / name for name in _LOG_NAMES]
    repo_root = Path(__file__).resolve().parents[3]
    paths.append(repo_root / _LOG_NAMES[0])
    return paths


def debug_session_log(
    *,
    location: str,
    message: str,
    data: dict[str, Any] | None = None,
    hypothesis_id: str = "",
    run_id: str = "pre-fix",
) -> None:
    # #region agent log
    payload = {
        "sessionId": _SESSION_ID,
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": message,
        "data": data or {},
        "hypothesisId": hypothesis_id,
        "runId": run_id,
    }
    line = json.dumps(payload, default=str) + "\n"
    for path in _log_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            continue
    # #endregion
