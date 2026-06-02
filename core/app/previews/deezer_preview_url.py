from __future__ import annotations

import time


def hdnea_exp_seconds(url: str) -> int | None:
    if "hdnea=" not in url:
        return None
    for part in url.split("hdnea=")[1].split("~"):
        if part.startswith("exp="):
            try:
                return int(part[4:])
            except ValueError:
                return None
    return None


def is_deezer_preview_url_expired(url: str, *, skew_seconds: int = 120) -> bool:
    """True when the signed CDN token is missing or within skew_seconds of expiry."""
    exp = hdnea_exp_seconds(url)
    if exp is None:
        return False
    return time.time() >= exp - skew_seconds
