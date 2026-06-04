from __future__ import annotations

import importlib.util
from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = CORE_ROOT / "scripts" / "smoke_essentia_tensorflow_real.py"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("smoke_essentia_tensorflow_real", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wav(tmp_path, content: bytes = b"\x01\x02\x03\x04") -> str:
    path = tmp_path / "smoke.wav"
    path.write_bytes(content)
    return str(path)


def test_run_smoke_model_missing(tmp_path, build_tf_models, make_tf_manager, fake_tf_backend):
    smoke = _load_smoke_module()
    mm = make_tf_manager(build_tf_models([]))

    report = smoke.run_smoke(
        manager=mm, backend=fake_tf_backend, wav_path=_wav(tmp_path), track_id=1
    )

    assert report["status"] == "model_missing"
    assert "discogs_effnet_bs64" in report["missing"]
    assert fake_tf_backend.calls == []


def test_run_smoke_real_output(tmp_path, build_tf_models, make_tf_manager, fake_tf_backend):
    smoke = _load_smoke_module()
    mm = make_tf_manager(
        build_tf_models(["discogs_effnet_bs64", "mood_happy_discogs_effnet"])
    )
    wav = _wav(tmp_path)

    report = smoke.run_smoke(manager=mm, backend=fake_tf_backend, wav_path=wav, track_id=1)

    assert report["status"] == "ok"
    assert report["embeddings_inference_mode"] == "real"
    assert report["classifier_inference_mode"] == "real"
    assert report["embedding_dimension"] and report["embedding_dimension"] >= 1
    assert report["classifier_count"] >= 1
    assert any(call[1] == wav for call in fake_tf_backend.calls)


def test_main_allow_missing_exit_zero(
    tmp_path, monkeypatch, build_tf_models, make_tf_manager, fake_tf_backend
):
    smoke = _load_smoke_module()
    mm = make_tf_manager(build_tf_models([]))
    monkeypatch.setattr(smoke, "ModelManager", lambda *a, **k: mm)
    monkeypatch.setattr(smoke, "EssentiaTensorflowBackend", lambda *a, **k: fake_tf_backend)

    code = smoke.main(["--allow-missing", "--wav-path", _wav(tmp_path)])
    assert code == 0


def test_main_require_models_exit_one_when_missing(
    tmp_path, monkeypatch, build_tf_models, make_tf_manager, fake_tf_backend
):
    smoke = _load_smoke_module()
    mm = make_tf_manager(build_tf_models([]))
    monkeypatch.setattr(smoke, "ModelManager", lambda *a, **k: mm)
    monkeypatch.setattr(smoke, "EssentiaTensorflowBackend", lambda *a, **k: fake_tf_backend)

    code = smoke.main(["--require-models", "--wav-path", _wav(tmp_path)])
    assert code == 1


def test_main_real_success_exit_zero(
    tmp_path, monkeypatch, build_tf_models, make_tf_manager, fake_tf_backend
):
    smoke = _load_smoke_module()
    mm = make_tf_manager(
        build_tf_models(["discogs_effnet_bs64", "mood_happy_discogs_effnet"])
    )
    monkeypatch.setattr(smoke, "ModelManager", lambda *a, **k: mm)
    monkeypatch.setattr(smoke, "EssentiaTensorflowBackend", lambda *a, **k: fake_tf_backend)

    code = smoke.main(["--require-models", "--wav-path", _wav(tmp_path)])
    assert code == 0
