import httpx
import pytest

from app.spotify.client import SpotifyClient, SpotifyHTTPError
from app.spotify.token_store import SpotifyTokenStore, StoredToken


class _MemTokenStore(SpotifyTokenStore):
    def __init__(self) -> None:
        self._tok: StoredToken | None = StoredToken(
            user_id="me",
            access_token="access",
            refresh_token="refresh",
            token_type="Bearer",
            scope="user-read-private",
            expires_at=None,
            raw={"access_token": "access", "refresh_token": "refresh", "token_type": "Bearer"},
        )

    def load(self) -> StoredToken | None:  # type: ignore[override]
        return self._tok

    def save_from_token_response(self, *, user_id: str, token_response: dict) -> StoredToken:  # type: ignore[override]
        self._tok = StoredToken(
            user_id=user_id,
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token"),
            token_type=token_response.get("token_type") or "Bearer",
            scope=token_response.get("scope") or "",
            expires_at=None,
            raw=token_response,
        )
        return self._tok


def test_pagination_saved_tracks() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/v1/me/tracks":
            q = dict(request.url.params)
            offset = int(q.get("offset", "0"))
            limit = int(q.get("limit", "50"))
            if offset == 0:
                body = {"items": [{"a": 1}], "next": "next", "total": 2}
            else:
                assert limit == 1
                body = {"items": [{"a": 2}], "next": None, "total": 2}
            return httpx.Response(200, json=body)
        return httpx.Response(404, json={"error": "nope"})

    transport = httpx.MockTransport(handler)
    client = SpotifyClient(
        token_store=_MemTokenStore(),
        transport=transport,
        sleeper=lambda *_: None,
    )

    items = client.iter_saved_tracks(limit=1)
    assert items == [{"a": 1}, {"a": 2}]
    assert any("offset=0" in u for u in calls)
    assert any("offset=1" in u for u in calls)


def test_refresh_on_401_then_success() -> None:
    state = {"me_calls": 0, "refresh_calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "accounts.spotify.com":
            state["refresh_calls"] += 1
            return httpx.Response(
                200,
                json={
                    "access_token": "new_access",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )

        if request.url.path == "/v1/me":
            state["me_calls"] += 1
            if state["me_calls"] == 1:
                return httpx.Response(401, json={"error": {"status": 401}})
            return httpx.Response(200, json={"id": "me"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    store = _MemTokenStore()
    client = SpotifyClient(token_store=store, transport=transport, sleeper=lambda *_: None)

    me = client.get_current_user()
    assert me["id"] == "me"
    assert state["refresh_calls"] == 1


def test_http_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"status": 403, "message": "forbidden"}})

    transport = httpx.MockTransport(handler)
    client = SpotifyClient(
        token_store=_MemTokenStore(),
        transport=transport,
        sleeper=lambda *_: None,
    )

    with pytest.raises(SpotifyHTTPError) as e:
        client.get_current_user()
    assert e.value.status_code == 403

