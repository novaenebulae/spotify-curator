from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AlbumCover:
    url: str | None
    width: int | None
    height: int | None


def extract_cover_from_images(images: list[Any] | None) -> AlbumCover:
    """Pick a thumbnail-sized Spotify album image URL (64–300px width preferred)."""
    if not images:
        return AlbumCover(None, None, None)

    parsed: list[tuple[int, int, str]] = []
    for img in images:
        if not isinstance(img, dict):
            continue
        url = img.get("url")
        if not url or not isinstance(url, str):
            continue
        width = int(img.get("width") or 0)
        height = int(img.get("height") or 0)
        parsed.append((width, height, url))

    if not parsed:
        return AlbumCover(None, None, None)

    in_range = [p for p in parsed if 64 <= p[0] <= 300]
    if in_range:
        chosen = min(in_range, key=lambda p: p[0])
    else:
        with_width = [p for p in parsed if p[0] > 0]
        chosen = min(with_width, key=lambda p: p[0]) if with_width else parsed[0]

    return AlbumCover(chosen[2], chosen[0] or None, chosen[1] or None)


def apply_cover_to_album(album: Any, cover: AlbumCover) -> None:
    album.cover_image_url = cover.url
    album.cover_image_width = cover.width
    album.cover_image_height = cover.height
