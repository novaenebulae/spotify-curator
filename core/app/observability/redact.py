from __future__ import annotations

import json
import re
from typing import Any

_TOKEN_KEYS = frozenset(
    {"access_token", "refresh_token", "token", "authorization", "client_secret", "api_key"}
)
_URL_AUTH_RE = re.compile(r"(https?://)[^\s]+(@)", re.IGNORECASE)
_WINDOWS_USER_PATH_RE = re.compile(r"[A-Za-z]:\\Users\\[^\\]+", re.IGNORECASE)


def redact_string(value: str) -> str:
    if not value:
        return value
    out = _URL_AUTH_RE.sub(r"\1[redacted]@", value)
    out = _WINDOWS_USER_PATH_RE.sub("[redacted-path]", out)
    if "access_token=" in out.lower() or "refresh_token=" in out.lower():
        return "[redacted-oauth-url]"
    return out


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, dict):
        return redact_dict(value)
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    return value


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in data.items():
        lk = key.lower()
        if lk in _TOKEN_KEYS:
            out[key] = "[redacted]"
        elif lk in ("url", "source_url") and isinstance(val, str):
            out[key] = "[redacted-url]" if val else val
        elif lk in ("temporary_path", "input_path", "output_path") and isinstance(val, str):
            out[key] = _basename_only(val)
        else:
            out[key] = redact_value(val)
    return out


def _basename_only(path: str) -> str:
    if not path:
        return path
    normalized = path.replace("\\", "/")
    parts = normalized.rstrip("/").split("/")
    if len(parts) >= 2:
        return f".../{parts[-2]}/{parts[-1]}"
    return parts[-1] if parts else path


def redact_json_text(text: str) -> str:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return redact_string(text)
    return json.dumps(redact_dict(parsed) if isinstance(parsed, dict) else redact_value(parsed))
