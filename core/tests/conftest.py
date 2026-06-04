import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

CORE_ROOT = Path(__file__).resolve().parents[1]

if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

os.environ.setdefault("PYTHONPATH", str(CORE_ROOT))


class FakeInferenceBackend:
    """Deterministic fake of TensorflowInferenceBackend for phase 6.8B tests.

    Scores derive from the WAV *contents*, so results change when the audio
    changes and reading ``wav_path`` is proven. No Essentia import.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    @staticmethod
    def _seed(wav_path: str) -> float:
        data = Path(wav_path).read_bytes()
        return int(hashlib.sha256(data).hexdigest()[:8], 16) / 0xFFFFFFFF

    def embeddings(self, wav_path: str, *, extractor_key: str) -> list[float]:
        self.calls.append(("embeddings", wav_path, extractor_key))
        base = self._seed(wav_path)
        if "effnet" in extractor_key:
            dim = 1280
        elif "musicnn" in extractor_key:
            dim = 200
        else:
            dim = 8
        return [(base + i * 0.0001) % 1.0 for i in range(dim)]

    def classifier_activations(
        self, wav_path: str, *, extractor_key: str, head_key: str
    ) -> list[tuple[str, float]]:
        self.calls.append(("activations", wav_path, head_key))
        base = self._seed(wav_path)
        if "genre" in head_key:
            return [(f"label_{i}", (base + i * 0.05) % 1.0) for i in range(5)]
        return [(head_key, base)]


@pytest.fixture
def fake_tf_backend() -> FakeInferenceBackend:
    return FakeInferenceBackend()


@pytest.fixture
def build_tf_models(tmp_path):
    """Create a temp Essentia models dir with .pb/.json at manifest paths.

    Returns a builder ``(keys, *, metadata=None) -> Path`` and a manager factory.
    """
    from app.models_registry.manager import ModelManager

    def _build(keys, *, metadata=None) -> Path:
        models_dir = tmp_path / "essentia_models"
        mm = ModelManager(models_dir=str(models_dir), verify_hash=False)
        for key in keys:
            entry = mm.get_entry(key)
            weights = models_dir / entry.local_weights_path
            meta = models_dir / entry.local_metadata_path
            weights.parent.mkdir(parents=True, exist_ok=True)
            meta.parent.mkdir(parents=True, exist_ok=True)
            weights.write_bytes(b"pb-bytes")
            meta.write_text(json.dumps((metadata or {}).get(key, {})), encoding="utf-8")
        return models_dir

    return _build


@pytest.fixture
def make_tf_manager():
    from app.models_registry.manager import ModelManager

    def _make(models_dir):
        return ModelManager(models_dir=str(models_dir), verify_hash=False)

    return _make


@pytest.fixture(autouse=True)
def _reset_sqlite_engine() -> None:
    from app.database.engine import reset_engine

    reset_engine()
    yield
    reset_engine()


@pytest.fixture
def audio_db(tmp_path, monkeypatch):
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from alembic import command
    from app.database.engine import reset_engine

    db_path = tmp_path / "audio_test.sqlite"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("CACHE_DIR", str(cache_dir))
    reset_engine()
    core_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(core_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(core_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                INSERT INTO tracks (id, name, normalized_title, duration_ms, created_at, updated_at)
                VALUES (1, 'Test Song', 'test song', 180000, datetime('now'), datetime('now'))
                """
            )
        )
        conn.commit()
    yield engine
    reset_engine()
