from __future__ import annotations

from pathlib import Path

from app.audio.tensorflow.segment_runner import SegmentTensorflowRunner


def test_segment_runner_unified_outputs(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    models_dir = build_tf_models(
        [
            "discogs_effnet_bs64",
            "discogs_maest_30s_pw_519l",
            "genre_discogs519_maest_519l",
            "mood_happy_discogs_effnet",
        ]
    )
    mm = make_tf_manager(models_dir)
    wav = tmp_path / "seg.wav"
    wav.write_bytes(b"\x00\x0a\x0b\x0c")

    runner = SegmentTensorflowRunner(model_manager=mm, backend=fake_tf_backend)
    result = runner.run_for_segment(segment_id=42, wav_path=str(wav))
    payload = runner.to_result_json(result, stage_name="essentia_tensorflow")

    assert payload["segment_id"] == 42
    assert payload["stage_name"] == "essentia_tensorflow"
    assert payload["inference"] == "real"
    assert "embedding_outputs" in payload
    assert "genre_outputs" in payload
    assert "classifier_outputs" in payload
    assert "mood_happy" in payload["classifier_outputs"]

    embedding_calls = [c for c in fake_tf_backend.calls if c[0] == "embeddings"]
    activation_calls = [c for c in fake_tf_backend.calls if c[0] == "activations"]
    assert len(embedding_calls) >= 1
    assert all(c[1] == str(wav) for c in embedding_calls + activation_calls)
