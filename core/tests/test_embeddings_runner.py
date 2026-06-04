from __future__ import annotations

from pathlib import Path

from app.audio.tensorflow.embeddings_runner import EFFNET_MODEL_KEY, EmbeddingsRunner
from app.audio.tensorflow.genre_runner import GENRE_MODEL_KEY, GenreRunner
from app.models_registry import ModelRegistry


def _models_dir(tmp_path: Path, *, with_effnet: bool, with_genre: bool) -> Path:
    models_dir = tmp_path / "models"
    if with_effnet:
        p = models_dir / "discogs_effnet" / "discogs-effnet-bs64-1.pb"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"effnet")
    if with_genre:
        p = models_dir / "discogs_maest" / "genre_discogs519-discogs-maest-30s-pw-519l.pb"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"genre")
    return models_dir


def test_embeddings_runner_vector_shape(tmp_path) -> None:
    registry = ModelRegistry(models_dir=str(_models_dir(tmp_path, with_effnet=True, with_genre=False)))
    result = EmbeddingsRunner(registry=registry).run_for_segment(segment_id=42, wav_path="/x.wav")
    assert EFFNET_MODEL_KEY in result.embedding_outputs
    out = result.embedding_outputs[EFFNET_MODEL_KEY]
    assert out["dimension"] == 1280
    assert len(out["vector"]) == 1280


def test_embeddings_runner_model_missing(tmp_path) -> None:
    registry = ModelRegistry(models_dir=str(_models_dir(tmp_path, with_effnet=False, with_genre=False)))
    result = EmbeddingsRunner(registry=registry).run_for_segment(segment_id=1, wav_path="/x.wav")
    assert result.embedding_outputs == {}
    assert EFFNET_MODEL_KEY in result.models_missing


def test_genre_runner_top_k(tmp_path) -> None:
    registry = ModelRegistry(models_dir=str(_models_dir(tmp_path, with_effnet=False, with_genre=True)))
    result = GenreRunner(registry=registry).run_for_segment(segment_id=7, wav_path="/x.wav")
    assert GENRE_MODEL_KEY in result.genre_outputs
    top_k = result.genre_outputs[GENRE_MODEL_KEY]["top_k"]
    assert len(top_k) >= 1
    assert "label" in top_k[0]
    assert "score" in top_k[0]
