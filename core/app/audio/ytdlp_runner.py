from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.audio.errors import YtDlpError
from app.audio.ytdlp_cmd import build_download_section_command, build_search_command
from app.settings.config import settings


def ytdlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def run_search(query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
    if not ytdlp_available():
        raise YtDlpError("YTDLP_NOT_FOUND", "yt-dlp binary not found on PATH")
    cmd = build_search_command(query, max_results=max_results)
    try:
        proc = subprocess.run(
            cmd.argv,
            capture_output=True,
            text=True,
            timeout=settings.ytdlp_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise YtDlpError("YTDLP_TIMEOUT", "yt-dlp search timed out", retryable=True) from e
    if proc.returncode != 0:
        raise YtDlpError("YTDLP_SEARCH_FAILED", (proc.stderr or proc.stdout or "search failed")[:500])
    entries: list[dict[str, Any]] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("_type") == "playlist" and "entries" in data:
            entries.extend(e for e in data["entries"] if e)
        else:
            entries.append(data)
    return entries[:max_results]


def run_download_section(
    url: str,
    *,
    start_seconds: float,
    end_seconds: float,
    output_template: Path,
) -> Path:
    if not ytdlp_available():
        raise YtDlpError("YTDLP_NOT_FOUND", "yt-dlp binary not found on PATH")
    output_template.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_download_section_command(
        url,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        output_path=str(output_template),
        audio_format=settings.ytdlp_format,
    )
    try:
        proc = subprocess.run(
            cmd.argv,
            capture_output=True,
            text=True,
            timeout=settings.ytdlp_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise YtDlpError("YTDLP_TIMEOUT", "yt-dlp download timed out", retryable=True) from e
    if proc.returncode != 0:
        raise YtDlpError(
            "YTDLP_DOWNLOAD_FAILED",
            (proc.stderr or proc.stdout or "download failed")[:500],
        )
    # Find downloaded file (template may use ext placeholder)
    parent = output_template.parent
    stem = output_template.name.split("%")[0]
    candidates = list(parent.glob(f"{stem}*"))
    if not candidates:
        raise YtDlpError("YTDLP_NO_OUTPUT", "yt-dlp did not produce an output file")
    return candidates[0]
