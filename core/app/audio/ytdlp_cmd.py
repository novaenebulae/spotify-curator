from __future__ import annotations

import shlex
from dataclasses import dataclass

from app.settings.config import settings


def _effective_youtube_player_client() -> str:
    configured = (settings.ytdlp_youtube_player_client or "").strip()
    if settings.ytdlp_cookies_file:
        # android/ios ignore --cookies; web/mweb/tv use them.
        if configured in ("android", "ios"):
            return "web"
        return configured or "web"
    return configured or "android"


def _ytdlp_base_argv() -> list[str]:
    argv = ["yt-dlp", "--remote-components", "ejs:github"]
    if settings.ytdlp_cookies_file:
        argv.extend(["--cookies", settings.ytdlp_cookies_file])
    client = _effective_youtube_player_client()
    if client:
        argv.extend(["--extractor-args", f"youtube:player_client={client}"])
    if settings.ytdlp_sleep_interval > 0:
        argv.extend(
            [
                "--sleep-interval",
                str(settings.ytdlp_sleep_interval),
                "--max-sleep-interval",
                str(settings.ytdlp_max_sleep_interval),
            ]
        )
    if settings.ytdlp_sleep_requests > 0:
        argv.extend(["--sleep-requests", str(settings.ytdlp_sleep_requests)])
    return argv


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
        *_ytdlp_base_argv(),
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
        *_ytdlp_base_argv(),
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
