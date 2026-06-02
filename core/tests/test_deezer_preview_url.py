import time

from app.previews.deezer_preview_url import (
    hdnea_exp_seconds,
    is_deezer_preview_url_expired,
)


def _signed_url(exp: int) -> str:
    return f"https://cdnt-preview.dzcdn.net/api/x.mp3?hdnea=exp={exp}~acl=*~hmac=deadbeef"


def test_hdnea_exp_seconds_parses() -> None:
    exp = int(time.time()) + 3600
    assert hdnea_exp_seconds(_signed_url(exp)) == exp


def test_is_expired_when_past_exp() -> None:
    past = int(time.time()) - 60
    assert is_deezer_preview_url_expired(_signed_url(past))


def test_is_not_expired_when_future_exp() -> None:
    future = int(time.time()) + 3600
    assert not is_deezer_preview_url_expired(_signed_url(future))


def test_unsigned_url_not_treated_as_expired() -> None:
    assert not is_deezer_preview_url_expired("https://cdns-preview.dzcdn.net/preview.mp3")
