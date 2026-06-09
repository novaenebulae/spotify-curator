from __future__ import annotations

import fcntl
import time
from pathlib import Path

from app.settings.config import settings


def throttle_ytdlp() -> None:
    """Serialize yt-dlp calls across downloader containers via shared data volume."""
    interval = settings.ytdlp_min_interval_seconds
    if interval <= 0:
        return
    state_path = Path(settings.data_dir) / ".ytdlp_throttle"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            raw = handle.read().strip()
            last = float(raw) if raw else 0.0
            now = time.time()
            wait = interval - (now - last)
            if wait > 0:
                time.sleep(wait)
            handle.seek(0)
            handle.truncate()
            handle.write(str(time.time()))
            handle.flush()
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
