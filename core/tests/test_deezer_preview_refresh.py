import time

import httpx
from sqlalchemy.orm import Session

from app.database.repositories.track_previews import TrackPreviewsRepository
from app.previews.deezer_client import DeezerClient
from app.previews.deezer_preview_refresh import refresh_stored_deezer_preview_url


def test_refresh_stored_preview_updates_db(audio_db) -> None:
    future = int(time.time()) + 7200
    fresh_preview = f"https://cdnt-preview.dzcdn.net/new.mp3?hdnea=exp={future}~acl=*~hmac=abc"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/track/12345"):
            return httpx.Response(
                200,
                json={
                    "id": 12345,
                    "title": "T",
                    "duration": 180,
                    "preview": fresh_preview,
                    "artist": {"name": "A"},
                    "album": {"title": "Al"},
                },
            )
        return httpx.Response(404)

    client = DeezerClient(transport=httpx.MockTransport(handler))
    previews = TrackPreviewsRepository()
    session = Session(audio_db)
    previews.upsert(
        session,
        track_id=1,
        provider="deezer",
        fields={
            "provider_track_id": "12345",
            "preview_url": f"https://old?hdnea=exp={int(time.time()) - 999}~acl=*",
            "is_available": True,
        },
    )
    session.commit()

    url = refresh_stored_deezer_preview_url(
        session,
        track_id=1,
        provider_track_id="12345",
        previews=previews,
        client=client,
    )
    session.commit()
    assert url == fresh_preview
    row = previews.get_for_track_provider(session, track_id=1, provider="deezer")
    assert row is not None
    assert row.preview_url == fresh_preview
