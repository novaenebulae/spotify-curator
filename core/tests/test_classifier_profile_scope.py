from __future__ import annotations

from pathlib import Path

from app.audio.tensorflow.classifier_runner import ClassifierRunner
from app.audio.tensorflow.genre_runner import GenreRunner
from app.audio.tensorflow.segment_runner import SegmentTensorflowRunner
from app.models_registry.profile_scope import model_keys_for_profile


def test_recommended_profile_excludes_musicnn_even_when_installed(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    models_dir = build_tf_models(
        [
            "discogs_effnet_bs64",
            "discogs_maest_30s_pw_519l",
            "genre_discogs519_maest_519l",
            "mood_happy_discogs_effnet",
            "msd_musicnn",
            "deam_msd_musicnn_2",
        ]
    )
    mm = make_tf_manager(models_dir)
    recommended = model_keys_for_profile("phase6-recommended", manager=mm)
    assert "msd_musicnn" not in recommended
    assert "deam_msd_musicnn_2" not in recommended

    wav = tmp_path / "seg.wav"
    wav.write_bytes(b"\x00\x0a")

    result = ClassifierRunner(model_manager=mm, backend=fake_tf_backend).run_for_segment(
        segment_id=1,
        wav_path=str(wav),
        model_profile="phase6-recommended",
    )

    assert "mood_happy" in result.classifier_outputs
    assert "arousal_valence" not in result.classifier_outputs
    musicnn_calls = [
        c for c in fake_tf_backend.calls if "musicnn" in c[2].lower() or c[2] == "deam_msd_musicnn_2"
    ]
    assert musicnn_calls == []


def test_full_profile_runs_arousal_valence_when_installed(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    models_dir = build_tf_models(
        [
            "discogs_effnet_bs64",
            "mood_happy_discogs_effnet",
            "msd_musicnn",
            "deam_msd_musicnn_2",
        ]
    )
    mm = make_tf_manager(models_dir)
    wav = tmp_path / "seg.wav"
    wav.write_bytes(b"\x01\x02")

    result = ClassifierRunner(model_manager=mm, backend=fake_tf_backend).run_for_segment(
        segment_id=2,
        wav_path=str(wav),
        model_profile="phase6-full",
    )

    assert "arousal_valence" in result.classifier_outputs
    assert any("musicnn" in c[2].lower() for c in fake_tf_backend.calls)


def test_minimal_profile_skips_genre_runner(tmp_path, build_tf_models, make_tf_manager, fake_tf_backend) -> None:
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
    wav.write_bytes(b"\x03\x04")

    genre = GenreRunner(model_manager=mm, backend=fake_tf_backend).run_for_segment(
        segment_id=3,
        wav_path=str(wav),
        model_profile="phase6-minimal",
    )

    assert genre.genre_outputs == {}
    assert genre.inference_mode == "none"
    assert fake_tf_backend.calls == []


def test_segment_runner_passes_profile_to_classifiers(
    tmp_path, build_tf_models, make_tf_manager, fake_tf_backend
) -> None:
    models_dir = build_tf_models(
        [
            "discogs_effnet_bs64",
            "discogs_maest_30s_pw_519l",
            "genre_discogs519_maest_519l",
            "mood_happy_discogs_effnet",
            "msd_musicnn",
            "deam_msd_musicnn_2",
        ]
    )
    mm = make_tf_manager(models_dir)
    wav = tmp_path / "seg.wav"
    wav.write_bytes(b"\x05\x06")

    runner = SegmentTensorflowRunner(model_manager=mm, backend=fake_tf_backend)
    result = runner.run_for_segment(
        segment_id=4, wav_path=str(wav), model_profile="phase6-recommended"
    )

    assert "mood_happy" in result.classifier_outputs
    assert "arousal_valence" not in result.classifier_outputs
    assert not any("musicnn" in c[2].lower() for c in fake_tf_backend.calls)
