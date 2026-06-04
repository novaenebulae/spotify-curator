from __future__ import annotations

from app.audio.tensorflow.classifier_runner import ClassifierRunner
from app.audio.tensorflow.embeddings_runner import EFFNET_MODEL_KEY, EmbeddingsRunner


def _wav(tmp_path, name: str, content: bytes) -> str:
    path = tmp_path / name
    path.write_bytes(content)
    return str(path)


def test_classifier_real_inference_outputs(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    models_dir = build_tf_models(
        [
            "discogs_effnet_bs64",
            "mood_happy_discogs_effnet",
            "voice_instrumental_discogs_effnet",
        ]
    )
    mm = make_tf_manager(models_dir)
    runner = ClassifierRunner(model_manager=mm, backend=fake_tf_backend)
    wav = _wav(tmp_path, "a.wav", b"\x10\x20\x30\x40")

    result = runner.run_for_segment(segment_id=1, wav_path=wav)

    assert result.inference_mode == "real"
    assert "mood_happy" in result.classifier_outputs
    assert result.classifier_outputs["mood_happy"]["inference_mode"] == "real"
    assert "probability" in result.classifier_outputs["mood_happy"]
    voice = result.classifier_outputs["voice_instrumental"]
    assert "voice_probability" in voice
    assert "instrumental_probability" in voice
    # arousal_valence head not installed -> reported missing, never faked.
    assert "arousal_valence" in result.models_missing
    assert "arousal_valence" not in result.classifier_outputs
    # wav_path was actually read by the backend.
    assert any(call[1] == wav for call in fake_tf_backend.calls)


def test_real_outputs_change_with_audio(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    models_dir = build_tf_models(["discogs_effnet_bs64", "mood_happy_discogs_effnet"])
    mm = make_tf_manager(models_dir)
    runner = ClassifierRunner(model_manager=mm, backend=fake_tf_backend)

    first = runner.run_for_segment(
        segment_id=1, wav_path=_wav(tmp_path, "first.wav", b"\x01\x01\x01\x01")
    )
    second = runner.run_for_segment(
        segment_id=1, wav_path=_wav(tmp_path, "second.wav", b"\xfe\xfe\xfe\xfe")
    )

    assert (
        first.classifier_outputs["mood_happy"]["probability"]
        != second.classifier_outputs["mood_happy"]["probability"]
    )


def test_embeddings_real_changes_with_audio(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    models_dir = build_tf_models(["discogs_effnet_bs64"])
    mm = make_tf_manager(models_dir)
    runner = EmbeddingsRunner(model_manager=mm, backend=fake_tf_backend)

    v1 = runner.run_for_segment(
        segment_id=1, wav_path=_wav(tmp_path, "x1.wav", b"\x01\x02")
    ).embedding_outputs[EFFNET_MODEL_KEY]["vector"]
    v2 = runner.run_for_segment(
        segment_id=1, wav_path=_wav(tmp_path, "x2.wav", b"\x09\x08")
    ).embedding_outputs[EFFNET_MODEL_KEY]["vector"]

    assert v1 != v2
