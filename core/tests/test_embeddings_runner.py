from __future__ import annotations

from app.audio.tensorflow.embeddings_runner import EFFNET_MODEL_KEY, EmbeddingsRunner
from app.audio.tensorflow.genre_runner import GENRE_MODEL_KEY, GenreRunner


def _wav(tmp_path, content: bytes = b"\x01\x02\x03\x04"):
    path = tmp_path / "seg.wav"
    path.write_bytes(content)
    return str(path)


def test_embeddings_runner_vector_shape(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
):
    models_dir = build_tf_models(["discogs_effnet_bs64"])
    mm = make_tf_manager(models_dir)
    result = EmbeddingsRunner(model_manager=mm, backend=fake_tf_backend).run_for_segment(
        segment_id=42, wav_path=_wav(tmp_path)
    )
    assert result.inference_mode == "real"
    assert EFFNET_MODEL_KEY in result.embedding_outputs
    out = result.embedding_outputs[EFFNET_MODEL_KEY]
    assert out["dimension"] == len(out["vector"]) >= 1
    assert out["inference_mode"] == "real"


def test_embeddings_runner_model_missing(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
):
    models_dir = build_tf_models([])
    mm = make_tf_manager(models_dir)
    result = EmbeddingsRunner(model_manager=mm, backend=fake_tf_backend).run_for_segment(
        segment_id=1, wav_path=_wav(tmp_path)
    )
    assert result.embedding_outputs == {}
    assert EFFNET_MODEL_KEY in result.models_missing
    assert result.inference_mode == "none"


def test_genre_runner_top_k(tmp_path, build_tf_models, make_tf_manager, fake_tf_backend):
    models_dir = build_tf_models(
        ["discogs_maest_30s_pw_519l", "genre_discogs519_maest_519l"]
    )
    mm = make_tf_manager(models_dir)
    result = GenreRunner(model_manager=mm, backend=fake_tf_backend).run_for_segment(
        segment_id=7, wav_path=_wav(tmp_path)
    )
    assert result.inference_mode == "real"
    assert GENRE_MODEL_KEY in result.genre_outputs
    top_k = result.genre_outputs[GENRE_MODEL_KEY]["top_k"]
    assert len(top_k) >= 1
    assert "label" in top_k[0]
    assert "score" in top_k[0]
