from __future__ import annotations

from app.audio.tensorflow.classifier_runner import ClassifierRunner
from app.audio.tensorflow.embeddings_runner import EFFNET_MODEL_KEY, EmbeddingsRunner
from app.audio.tensorflow.errors import InferenceError, TENSORFLOW_INFERENCE_FAILED
from app.audio.tensorflow.genre_runner import GENRE_MODEL_KEY, GenreRunner


def _wav(tmp_path) -> str:
    path = tmp_path / "seg.wav"
    path.write_bytes(b"\x00\x01")
    return str(path)


def test_classifier_model_missing_no_fake(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    mm = make_tf_manager(build_tf_models([]))
    result = ClassifierRunner(model_manager=mm, backend=fake_tf_backend).run_for_segment(
        segment_id=1, wav_path=_wav(tmp_path)
    )
    assert result.classifier_outputs == {}
    assert "mood_happy" in result.models_missing
    assert "arousal_valence" in result.models_missing
    assert result.inference_mode == "none"
    # No backend call happened since nothing was available.
    assert fake_tf_backend.calls == []


def test_classifier_head_missing_when_extractor_only(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    # EffNet present but no heads -> every classifier reported missing.
    mm = make_tf_manager(build_tf_models(["discogs_effnet_bs64"]))
    result = ClassifierRunner(model_manager=mm, backend=fake_tf_backend).run_for_segment(
        segment_id=1, wav_path=_wav(tmp_path)
    )
    assert result.classifier_outputs == {}
    assert "mood_happy" in result.models_missing


def test_embeddings_and_genre_model_missing(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    mm = make_tf_manager(build_tf_models([]))
    emb = EmbeddingsRunner(model_manager=mm, backend=fake_tf_backend).run_for_segment(
        segment_id=1, wav_path=_wav(tmp_path)
    )
    genre = GenreRunner(model_manager=mm, backend=fake_tf_backend).run_for_segment(
        segment_id=1, wav_path=_wav(tmp_path)
    )
    assert EFFNET_MODEL_KEY in emb.models_missing
    assert emb.embedding_outputs == {}
    assert GENRE_MODEL_KEY in genre.models_missing
    assert genre.genre_outputs[GENRE_MODEL_KEY]["error_code"] == "MODEL_NOT_ON_DISK"


def test_genre_audio_too_short_treated_as_model_missing(
    tmp_path, build_tf_models, make_tf_manager
) -> None:
    class ShortAudioBackend:
        def classifier_activations(self, wav_path: str, *, extractor_key: str, head_key: str):
            raise InferenceError(
                code=TENSORFLOW_INFERENCE_FAILED,
                message="Head inference failed: input signal is too short",
            )

    mm = make_tf_manager(
        build_tf_models(["discogs_maest_30s_pw_519l", "genre_discogs519_maest_519l"])
    )
    result = GenreRunner(model_manager=mm, backend=ShortAudioBackend()).run_for_segment(
        segment_id=1, wav_path=_wav(tmp_path)
    )
    assert GENRE_MODEL_KEY not in result.models_missing
    assert result.genre_outputs[GENRE_MODEL_KEY]["error_code"] == "AUDIO_TOO_SHORT"
    assert result.inference_mode == "none"
