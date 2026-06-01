from __future__ import annotations

import shlex
from dataclasses import dataclass


@dataclass(frozen=True)
class YtDlpSearchCommand:
    argv: list[str]


@dataclass(frozen=True)
class YtDlpDownloadCommand:
    argv: list[str]
    output_path: str


def build_search_command(query: str, *, max_results: int = 5) -> YtDlpSearchCommand:
    safe_query = query.replace('"', "")
    argv = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--no-playlist",
        "--no-warnings",
        f"ytsearch{max_results}:{safe_query}",
    ]
    return YtDlpSearchCommand(argv=argv)


def build_download_section_command(
    url: str,
    *,
    start_seconds: float,
    end_seconds: float,
    output_path: str,
    audio_format: str,
) -> YtDlpDownloadCommand:
    section = f"*{start_seconds:.3f}-{end_seconds:.3f}"
    argv = [
        "yt-dlp",
        "-f",
        audio_format,
        "--no-playlist",
        "--force-keyframes-at-cuts",
        "--download-sections",
        section,
        "-o",
        output_path,
        "--no-warnings",
        url,
    ]
    return YtDlpDownloadCommand(argv=argv, output_path=output_path)


def argv_to_log_string(argv: list[str]) -> str:
    return " ".join(shlex.quote(a) for a in argv)
