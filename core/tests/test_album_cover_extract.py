from app.library.album_cover import extract_cover_from_images


def test_extract_prefers_thumbnail_size() -> None:
    images = [
        {"url": "https://i.scdn.co/image/large", "width": 640, "height": 640},
        {"url": "https://i.scdn.co/image/med", "width": 300, "height": 300},
        {"url": "https://i.scdn.co/image/small", "width": 64, "height": 64},
    ]
    cover = extract_cover_from_images(images)
    assert cover.url == "https://i.scdn.co/image/small"
    assert cover.width == 64
    assert cover.height == 64


def test_extract_smallest_when_no_thumbnail_range() -> None:
    images = [
        {"url": "https://i.scdn.co/image/large", "width": 640, "height": 640},
    ]
    cover = extract_cover_from_images(images)
    assert cover.url == "https://i.scdn.co/image/large"


def test_extract_empty_images() -> None:
    cover = extract_cover_from_images([])
    assert cover.url is None
