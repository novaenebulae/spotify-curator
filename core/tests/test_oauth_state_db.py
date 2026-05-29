
from app.database.engine import reset_engine
from app.database.init_db import init_db
from app.spotify.oauth_state import OAuthStateStore


def test_oauth_state_survives_engine_reset(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "oauth.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    reset_engine()
    init_db()

    store = OAuthStateStore(ttl_seconds=600)
    store.put("state-abc", "verifier-xyz")

    reset_engine()
    init_db()

    store2 = OAuthStateStore(ttl_seconds=600)
    popped = store2.pop("state-abc")
    assert popped is not None
    assert popped.code_verifier == "verifier-xyz"
